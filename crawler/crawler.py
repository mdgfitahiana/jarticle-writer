# crawler/crawler.py

import time, requests
from typing import List, Dict, Tuple
from collections import deque
from config import HEADERS, DEFAULT_TIMEOUT
from utils.url_utils import normalize_url, same_domain, is_pdf_url
from utils.robots_utils import allowed_by_robots
from utils.parsing import extract_text_and_links, extract_pdf_text
from utils.ai_relevance import check_relevance_with_ai
from utils.date_utils import get_date_from_headers, get_date_from_html, get_date_from_text_ai
from utils.summarizer import summarize_content

def crawl_site(seed_url: str, max_depth: int = 1, max_pages: int = 25,
               delay: float = 0.5, respect_robots: bool = True) -> List[Dict]:

    seed = normalize_url(seed_url)
    results, visited = [], set()
    q = deque([(seed, 0, [])])
    pages_processed = 0

    print(f"[CRAWLER] Starting crawl from: {seed}")

    def sort_priority(link_tuple: Tuple[str, int, list]) -> int:
        url, _, _ = link_tuple
        if ".pdf" in url.lower(): return 0
        if "finance" in url.lower() or "press" in url.lower(): return 1
        return 2

    while q and pages_processed < max_pages:
        q = deque(sorted(list(q), key=sort_priority))
        url, depth, parent_urls = q.popleft()

        if url in visited:
            continue
        visited.add(url)

        if respect_robots and not allowed_by_robots(url):
            continue

        if delay > 0:
            time.sleep(delay)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT, stream=True)
            if not resp.ok:
                continue

            content_type = resp.headers.get("Content-Type", "").lower()
            print(f"[DEBUG] URL = {url}, Content-Type = {content_type}")

            # ------------------- PDF -------------------
            if is_pdf_url(url, content_type):
                print(f"[DEBUG] PDF détecté : {url}")

                pdf_bytes = resp.content
                pdf_text = extract_pdf_text(pdf_bytes)

                # --- AI date extraction ---
                last_date = get_date_from_headers(resp)  # fallback
                ai_date = get_date_from_text_ai(pdf_text)
                if ai_date != "Non trouvé":
                    last_date = ai_date

                purpose = """
                Collecter toutes les informations pertinentes sur l'entreprise, incluant :
                - Les rapports financiers et résultats (bilans, comptes annuels, chiffres clés),
                - Les communiqués de presse officiels,
                - Les actualités importantes concernant l'entreprise (nouveaux partenariats, fusions, acquisitions, changements dans la direction, etc.).
                Répondre uniquement si le texte est pertinent pour ces critères.
                """

                is_relevant = check_relevance_with_ai(pdf_text, purpose=purpose)

                if is_relevant:
                    results.append({
                        "seed": seed,
                        "url": url,
                        "title": "PDF Document",
                        "content": pdf_text,
                        "matched_keywords": "AI-Relevant",
                        "snippet": pdf_text[:1500],
                        "last_date": last_date,
                        "summary": summarize_content(pdf_text) if pdf_text else "",
                        "pdf_source": {
                            "pdf_url": url,
                            "parent_urls": parent_urls
                        }
                    })
                pages_processed += 1

            # ------------------- HTML -------------------
            elif "html" in content_type:
                text, links, title = extract_text_and_links(resp.text, resp.url)

                # --- AI date extraction ---
                last_date = get_date_from_html(resp.text, resp)  # fallback
                ai_date = get_date_from_text_ai(text)
                if ai_date != "Non trouvé":
                    last_date = ai_date

                purpose = """
                Collecter toutes les informations pertinentes sur l'entreprise, incluant :
                - Les rapports financiers et résultats (bilans, comptes annuels, chiffres clés),
                - Les communiqués de presse officiels,
                - Les actualités importantes concernant l'entreprise (nouveaux partenariats, fusions, acquisitions, changements dans la direction, etc.).
                Répondre uniquement si le texte est pertinent pour ces critères.
                """

                is_relevant = check_relevance_with_ai(text, purpose=purpose)

                if is_relevant:
                    results.append({
                        "seed": seed,
                        "url": url,
                        "title": title,
                        "content": text,
                        "matched_keywords": "AI-Relevant",
                        "snippet": text[:1500],
                        "last_date": last_date,
                        "summary": summarize_content(text) if text else "",
                        "pdf_source": {
                            "pdf_url": "",           # Not a PDF itself
                            "parent_urls": [url]     # This page can be n-1 for PDFs
                        }
                    })
                pages_processed += 1

                # Discover new links
                if depth < max_depth:
                    for link in links:
                        if same_domain(link, seed) and link not in visited:
                            q.append((link, depth+1, parent_urls + [url]))

        except Exception as e:
            print(f"[ERROR][REQUEST] {url} | {e}")
            continue

    print(f"[CRAWLER] Finished. Processed {pages_processed} pages. Results found: {len(results)}")
    return results
