from __future__ import annotations
from typing import Optional, Sequence, Mapping, Any, Tuple

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .engine import session_scope
from .models import EmbeddingArticle as Article
from .config import get_settings

cfg = get_settings()

# Tunables (good starting points; override via env/secrets if needed)
DUPLICATE_DISTANCE = float(cfg.get("DUPLICATE_DISTANCE", 0.03))  # same/near-same content
CHANGE_DISTANCE     = float(cfg.get("CHANGE_DISTANCE", 0.12))    # meaningful change for same URL
SEARCH_K            = int(cfg.get("NEAR_DUP_K", 3))
PROBES              = int(cfg.get("set_ivfflat_probes", 10))

# --------------------- helpers ---------------------

def canonical_url_of(resource: Mapping[str, Any]) -> Optional[str]:
    """HTML: resource['url'] ; PDF: resource['pdf_source']['pdf_url']."""
    pdf_url = (resource.get("pdf_source") or {}).get("pdf_url") or ""
    url = resource.get("url") or ""
    return (pdf_url or url) or None

def build_metadata_envelope(*, resource: Mapping[str, Any], hash_str: str | None,
                            content_type: str) -> dict:
    """Always include keys (even when None) so metadata is stable."""
    pdf_src = resource.get("pdf_source") or {}
    return {
        "title": resource.get("title"),
        "url": canonical_url_of(resource),
        "source": resource.get("seed"),
        "last_date": resource.get("last_date"),
        "snippet": resource.get("snippet"),
        "summary": resource.get("summary"),
        "pdf_source": {
            "pdf_url": pdf_src.get("pdf_url"),
            "parent_urls": pdf_src.get("parent_urls") or [],
        },
        "matched_keywords": resource.get("matched_keywords"),
        "hash": hash_str,
        "seed": resource.get("seed"),
        "content_type": content_type,  # "html" | "pdf"
        "version": 1,
    }

# --------------------- reads / writes ---------------------

def get_hash_by_url(session: Session, url: str) -> Optional[str]:
    row = session.execute(
        select(Article.metadata_).where(Article.url == url)
    ).scalar_one_or_none()
    if not row:
        return None
    return (row or {}).get("hash")

def upsert_article_by_url(
    session: Session,
    *,
    url: str,
    title: Optional[str],
    content: str,
    embedding: Sequence[float],
    source: Optional[str],
    metadata_envelope: dict,
    sent_to_stakeholders: Optional[bool] = None,
) -> Article:
    """Insert or update by URL (conflicts only if url is NOT NULL)."""
    values = dict(
        title=title,
        content=content,
        embedding=list(embedding),
        source=source,
        url=url,
        metadata_=metadata_envelope,  # ORM attr -> DB column "metadata"
        sent_to_stakeholders=sent_to_stakeholders,
    )

    # Build the INSERT first...
    ins = insert(Article).values(**values)

    # ...then reference its `excluded` (uses DB column names)
    stmt = ins.on_conflict_do_update(
        index_elements=[Article.url],               # matches partial unique index on (url)
        index_where=Article.url.isnot(None),        # required because the index is partial (url IS NOT NULL)
        set_={
            "title": ins.excluded.title,
            "content": ins.excluded.content,
            "embedding": ins.excluded.embedding,
            "source": ins.excluded.source,
            "metadata": ins.excluded.metadata,                  # <-- column name, not "metadata_"
            "sent_to_stakeholders": ins.excluded.sent_to_stakeholders,
        },
    ).returning(Article)

    return session.scalars(stmt).first()

# --------- convenience wrappers with automatic sessions ----------

def get_hash_by_url_tx(url: str) -> Optional[str]:
    with session_scope() as s:
        return get_hash_by_url(s, url)

def upsert_article_by_url_tx(**kwargs) -> Article:
    with session_scope() as s:
        return upsert_article_by_url(s, **kwargs)

def vector_knn_tx(query_vec: Sequence[float], k: int = 10, probes: int | None = None):
    """Read example: cosine KNN (matches your IVFFlat opclass)."""
    with session_scope() as s:
        s.execute(text(f"set local ivfflat.probes = {int(probes or PROBES)}"))
        dist = Article.embedding.cosine_distance(list(query_vec)).label("dist")
        stmt = select(Article).order_by(dist).limit(k)
        return list(s.scalars(stmt))

# --------------------- similarity policy ---------------------

def distance_to_url(session: Session, url: str, vec: Sequence[float]) -> Optional[float]:
    """Return cosine distance between provided vector and stored row for this URL, or None if missing."""
    stmt = (
        select(Article.embedding.cosine_distance(list(vec)).label("dist"))
        .where(Article.url == url)
        .limit(1)
    )
    return session.execute(stmt).scalar_one_or_none()

def topk_nearest(session: Session, vec: Sequence[float], k: int = SEARCH_K) -> list[Tuple[str, float]]:
    """Return [(url, distance)] for top-k nearest rows by cosine distance."""
    session.execute(text(f"SET LOCAL ivfflat.probes = {int(PROBES)}"))
    dist = Article.embedding.cosine_distance(list(vec)).label("dist")
    stmt = select(Article.url, dist).order_by(dist).limit(k)
    rows = session.execute(stmt).all()
    return [(u, float(d)) for (u, d) in rows if u is not None]

def add_alias_url(session: Session, canonical_url: str, alias_url: str) -> None:
    """Append alias_url into metadata.alias_urls (read-modify-write in Python for simplicity)."""
    row = session.execute(select(Article).where(Article.url == canonical_url)).scalar_one_or_none()
    if not row:
        return
    md = dict(row.metadata_ or {})
    aliases = list(md.get("alias_urls") or [])
    if alias_url and alias_url not in aliases:
        aliases.append(alias_url)
        md["alias_urls"] = aliases
        row.metadata_ = md
        session.add(row)

def upsert_by_similarity(
    session: Session,
    *,
    resource: Mapping[str, Any],
    embedding: Sequence[float],
    metadata_envelope: dict,
) -> Tuple[str, Optional[float]]:
    """
    Decide insert/update/skip using cosine distance thresholds.
    Returns ("skipped"|"updated"|"inserted", distance_or_None).
    """
    url = canonical_url_of(resource)
    if not url:
        return ("skipped", None)

    # 1) If we already have this URL, compare distances for change detection.
    dist_same = distance_to_url(session, url, embedding)
    if dist_same is not None:
        if dist_same <= DUPLICATE_DISTANCE:
            return ("skipped", dist_same)  # no meaningful change
        elif dist_same >= CHANGE_DISTANCE:
            # significant update: update row via upsert
            upsert_article_by_url(
                session,
                url=url,
                title=resource.get("title"),
                content=resource["content"],
                embedding=embedding,
                source=resource.get("seed"),
                metadata_envelope=metadata_envelope,
                sent_to_stakeholders=False,
            )
            return ("updated", dist_same)
        else:
            return ("skipped", dist_same)  # minor change

    # 2) New URL: near-duplicate check against existing rows
    neighbors = topk_nearest(session, embedding, k=SEARCH_K)
    if neighbors:
        best_url, best_dist = neighbors[0]
        if best_dist <= DUPLICATE_DISTANCE:
            add_alias_url(session, canonical_url=best_url, alias_url=url)
            return ("skipped", best_dist)

    # 3) Not a duplicate → insert new
    upsert_article_by_url(
        session,
        url=url,
        title=resource.get("title"),
        content=resource["content"],
        embedding=embedding,
        source=resource.get("seed"),
        metadata_envelope=metadata_envelope,
        sent_to_stakeholders=False,
    )
    return ("inserted", None)
