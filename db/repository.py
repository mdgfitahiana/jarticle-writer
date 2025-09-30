from __future__ import annotations
from typing import Iterable, Sequence, Optional
from sqlalchemy import select, update, delete, text
from sqlalchemy.orm import Session

from .engine import session_scope, get_session_factory
from .models import EmbeddingArticle as Article
from .config import get_settings

cfg = get_settings()

# ---------- CREATE ----------
def create_article(
    session: Session,
    *,
    title: Optional[str],
    content: str,
    embedding: Sequence[float],
    source: Optional[str] = None,
    url: Optional[str] = None,
    metadata: Optional[dict] = None,
    sent_to_stakeholders: Optional[bool] = None,
) -> Article:
    a = Article(
        title=title,
        content=content,
        embedding=list(embedding),
        source=source,
        url=url,
        metadata_=metadata,
        sent_to_stakeholders=sent_to_stakeholders,
    )
    session.add(a)
    session.flush()  # get ID
    return a

# ---------- READ ----------
def get_article(session: Session, article_id) -> Optional[Article]:
    return session.get(Article, article_id)

def list_articles(session: Session, *, limit: int = 50, offset: int = 0) -> list[Article]:
    stmt = select(Article).order_by(Article.created_at.desc()).limit(limit).offset(offset)
    return list(session.scalars(stmt))

# ---------- UPDATE ----------
def update_article(
    session: Session, article_id, **fields
) -> Optional[Article]:
    # map Python key 'metadata' -> column 'metadata_'
    if "metadata" in fields:
        fields["metadata_"] = fields.pop("metadata")
    stmt = (
        update(Article)
        .where(Article.id == article_id)
        .values(**fields)
        .returning(Article)
    )
    return session.scalars(stmt).first()

# ---------- DELETE ----------
def delete_article(session: Session, article_id) -> bool:
    res = session.execute(delete(Article).where(Article.id == article_id))
    return res.rowcount > 0

# ---------- VECTOR SEARCH (cosine) ----------
def search_by_vector(
    session: Session,
    query_vec: Sequence[float],
    *,
    k: int = 10,
    probes: int | None = None,
) -> list[Article]:
    """
    Uses cosine distance to match your IVFFlat(vector_cosine_ops) index.
    Optionally bumps ivfflat.probes for better recall.
    """
    probes = probes or cfg["set_ivfflat_probes"]
    # Improve recall (temporary for this transaction)
    session.execute(text(f"SET LOCAL ivfflat.probes = {int(probes)}"))
    stmt = (
        select(Article)
        .order_by(Article.embedding.cosine_distance(list(query_vec)))
        .limit(k)
    )
    return list(session.scalars(stmt))

# Convenience helpers that manage the session for you --------------------------
def create_article_tx(**kwargs) -> Article:
    with session_scope() as s:
        return create_article(s, **kwargs)

def get_article_tx(article_id) -> Optional[Article]:
    with session_scope() as s:
        return get_article(s, article_id)

def list_articles_tx(limit: int = 50, offset: int = 0) -> list[Article]:
    with session_scope() as s:
        return list_articles(s, limit=limit, offset=offset)

def update_article_tx(article_id, **fields) -> Optional[Article]:
    with session_scope() as s:
        return update_article(s, article_id, **fields)

def delete_article_tx(article_id) -> bool:
    with session_scope() as s:
        return delete_article(s, article_id)

def search_by_vector_tx(query_vec, *, k: int = 10, probes: int | None = None) -> list[Article]:
    with session_scope() as s:
        return search_by_vector(s, query_vec, k=k, probes=probes)
