# crawler/crawler.py

import time, requests
from typing import List, Dict, Tuple
from collections import deque, defaultdict
from config import HEADERS, DEFAULT_TIMEOUT
from utils.url_utils import normalize_url, same_domain, is_pdf_url
from utils.robots_utils import allowed_by_robots
from utils.parsing import extract_text_and_links, extract_pdf_text
from utils.ai_relevance import check_relevance_with_ai

def crawl_site(seed_url: str, max_depth: int = 1, max_pages: int = 25,
               delay: float = 0.5, respect_robots: bool = True) -> List[Dict]:
    seed = normalize_url(seed_url)
    results, visited = [], set()

    # Queue holds tuples: (url, depth, parent_urls)
    q = deque([(seed, 0, [])])
    pages_processed = 0

    # Track all parent URLs for PDFs
    pdf_parents = defaultdict(list)

    print(f"[CRAWLER] Starting crawl from: {seed}")
    print(f"[CRAWLER] max_depth={max_depth}, max_pages={max_pages}, delay={delay}, respect_robots={respect_robots}")

    def sort_priority(link_tuple: Tuple[str, int, List[str]]) -> int:
        url, _, _ = link_tuple
        if ".pdf" in url.lower():
            return 0
        if "finance" in url.lower() or "press" in url.lower():
            return 1
        return 2

    while q and pages_processed < max_pages:
        # Re-sort queue at each iteration
        q = deque(sorted(list(q), key=sort_priority))

        url, depth, parent_urls = q.popleft()
        print(f"\n[QUEUE] Popped: {url} (depth={depth})")

        if url in visited:
            print(f"[VISITED] Already visited, skipping: {url}")
            continue
        visited.add(url)

        if respect_robots and not allowed_by_robots(url):
            print(f"[ROBOTS] Blocked by robots.txt, skipping: {url}")
            continue

        if delay > 0:
            print(f"[DELAY] Sleeping {delay}s before fetching {url}")
            time.sleep(delay)

        try:
            print(f"[REQUEST] Fetching: {url}")
            resp = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT, stream=True)
            if not resp.ok:
                print(f"[REQUEST] Failed: {url} (status={resp.status_code})")
                continue

            content_type = resp.headers.get("Content-Type", "").lower()
            print(f"[CONTENT] Detected content-type={content_type}")

            # Case 1: PDF file
            if is_pdf_url(url, content_type):
                print(f"[PDF] Detected PDF: {url}")
                try:
                    pdf_bytes = resp.content
                    print(f"[PDF] Downloaded {len(pdf_bytes)} bytes from {url}")

                    pdf_text = extract_pdf_text(pdf_bytes)
                    print(f"[PDF] Extracted text length={len(pdf_text)}")

                    purpose_text = """
                    Classifier le document PDF parmi :
                    - Rapport financier (annuel, trimestriel, résultats)
                    - Communiqué de presse
                    - Document non pertinent
                    """

                    is_relevant = check_relevance_with_ai(pdf_text, purpose_text)
                    if is_relevant:
                        print(f"[AI] PDF classified as relevant")
                        results.append({
                            "seed": seed,
                            "url": url,
                            "title": "PDF Document",
                            "content": pdf_text,
                            "matched_keywords": "AI-Relevant",
                            "snippet": pdf_text[:1500],
                            "pdf_source": {
                                "pdf_url": url,
                                "parent_urls": parent_urls
                            }
                        })
                    else:
                        print(f"[AI] PDF not relevant: {url}")

                    pages_processed += 1
                    print(f"[COUNTER] pages_processed={pages_processed}")

                except Exception as e:
                    print(f"[ERROR][PDF] Exception during PDF handling: {url} | {e}")
                    continue

            # Case 2: HTML page
            elif "html" in content_type:
                print(f"[HTML] Detected HTML page: {url}")
                try:
                    text, links, title = extract_text_and_links(resp.text, resp.url)
                    print(f"[HTML] Extracted text length={len(text)}, links={len(links)}, title='{title}'")

                    purpose_text = """
                    Identifier et classifier les informations financières et patrimoniales :
                    - Rapports financiers annuels/trimestriels
                    - Communiqués de presse
                    - Documents financiers pertinents
                    - Écarter les documents non pertinents
                    """

                    is_relevant = check_relevance_with_ai(text, purpose_text)
                    if is_relevant:
                        print(f"[AI] HTML page classified as relevant")
                        results.append({
                            "seed": seed,
                            "url": url,
                            "title": title,
                            "content": text,
                            "matched_keywords": "AI-Relevant",
                            "snippet": text[:1500]
                        })
                    else:
                        print(f"[AI] HTML page not relevant: {url}")

                    pages_processed += 1
                    print(f"[COUNTER] pages_processed={pages_processed}")

                    # Discover new links, attach current page as parent
                    if depth < max_depth:
                        new_links = []
                        for link in links:
                            if same_domain(link, seed) and link not in visited:
                                new_links.append((link, depth + 1, parent_urls + [url]))
                        print(f"[QUEUE] Adding {len(new_links)} new links from {url}")
                        q.extend(new_links)

                except Exception as e:
                    print(f"[ERROR][HTML] Exception during HTML handling: {url} | {e}")
                    continue

            else:
                print(f"[SKIP] Unsupported content-type for {url} ({content_type})")

        except Exception as e:
            print(f"[ERROR][REQUEST] Exception during request for {url} | {e}")
            continue

    print(f"\n[CRAWLER] Finished. Processed {pages_processed} pages. Results found: {len(results)}")
    return results
