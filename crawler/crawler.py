import re, time, requests
from collections import deque
from veille_finance.config import HEADERS, DEFAULT_TIMEOUT
from veille_finance.utils.url_utils import normalize_url, same_domain
from veille_finance.utils.robots_utils import allowed_by_robots
from veille_finance.utils.robots_utils import allowed_by_robots
from veille_finance.utils.parsing import extract_text_and_links

def crawl_site(seed_url: str, keywords: list, max_depth: int = 1, max_pages: int = 25,
               delay: float = 0.5, respect_robots: bool = True):
    seed = normalize_url(seed_url)
    results, visited = [], set()
    q = deque([(seed, 0)])
    pages_processed = 0

    while q and pages_processed < max_pages:
        url, depth = q.popleft()
        if url in visited:
            continue
        visited.add(url)

        if respect_robots and not allowed_by_robots(url):
            continue

        if delay > 0:
            time.sleep(delay)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
            if not resp.ok or "html" not in resp.headers.get("Content-Type", "").lower():
                continue

            text, links, title = extract_text_and_links(resp.text, resp.url)
            ltext, lurl = (text or "").lower(), (resp.url or "").lower()

            matched = [kw for kw in keywords if kw.lower() in ltext or kw.lower() in lurl]

            if matched:
                snippet = re.sub(r"\s+", " ", ltext)[:1500]
                results.append({
                    "seed": seed,
                    "url": resp.url,
                    "title": title,
                    "matched_keywords": ", ".join(sorted(set(matched), key=str.lower)),
                    "snippet": snippet
                })

            pages_processed += 1

            if depth < max_depth:
                for link in links:
                    if same_domain(link, seed) and link not in visited:
                        q.append((link, depth + 1))
        except Exception:
            continue

    return results
