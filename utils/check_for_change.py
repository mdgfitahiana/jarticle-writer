from typing import List, Dict, Union
from utils.hash_utils import compute_page_hash
from crawler.crawler import crawl_site
from db.repository import get_hash_by_url_tx, upsert_article_by_url_tx, canonical_url_of, build_metadata_envelope, upsert_by_similarity
from utils.embeddings import embed_text


def check_for_change(
    seed_url: str,
    max_depth: int = 1,
    max_pages: int = 25,
    delay: float = 0.5,
    respect_robots: bool = True,
    output_bool: bool = True,
) -> Union[bool, List[Dict]]:
    """
    Pure function: crawl a site, detect changes, return results.
    """

    # Step 1: crawl resources
    resources = crawl_site(seed_url, max_depth, max_pages, delay, respect_robots)

    # Step 2: prepare sources from resources
    sources: Dict[str, Dict[str, str]] = {}
    for r in resources:
        pdf_info = r.get("pdf_source", {})
        for parent_url in pdf_info.get("parent_urls", []):
            if parent_url not in sources:
                sources[parent_url] = {"hash": "", "last_date": ""}

    # Step 3: compute hash and detect changes
    changes_detected = False
    changed_resources: List[Dict] = []

    for parent_url in sources:
        try:
            current_hash = compute_page_hash(parent_url)
        except Exception:
            current_hash = ""

        prev_hash = sources[parent_url]["hash"]
        if prev_hash != current_hash:

            changes_detected = True
            sources[parent_url]["hash"] = current_hash  # you can delete this later if not used

            for r in resources:
                if parent_url in r.get("pdf_source", {}).get("parent_urls", []):
                    sources[parent_url]["last_date"] = r.get("last_date", "")

                    # Decide canonical URL; skip if none
                    url_canon = canonical_url_of(r)
                    if not url_canon:
                        continue

                    # --- compute embedding (must match your fixed DIM) ---
                    vec = embed_text(r["content"])

                    # --- metadata envelope (always include keys, even if None) ---
                    md = build_metadata_envelope(
                        resource=r,
                        hash_str=None,  # hash no longer used
                        content_type="pdf" if r.get("pdf_source", {}).get("pdf_url") else "html",
                    )

                    # --- upsert by similarity policy ---
                    from db.engine import session_scope
                    with session_scope() as s:
                        action, dist = upsert_by_similarity(
                            s,
                            resource=r,
                            embedding=vec,
                            metadata_envelope=md,
                        )
                        # optionally log
                        # print(f"[UPSERT] {action} url={url_canon} dist={dist}")
                    if not output_bool:
                        changed_resources.append(r)


    return changes_detected if output_bool else changed_resources
