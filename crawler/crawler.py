import re, time, requests
from typing import List, Dict
from collections import deque
from config import HEADERS, DEFAULT_TIMEOUT
from utils.url_utils import normalize_url, same_domain
from utils.robots_utils import allowed_by_robots
from utils.robots_utils import allowed_by_robots
from utils.parsing import extract_text_and_links
from utils.ai_relevance import ai_match_result


def crawl_site(seed_url: str, max_depth: int = 1, max_pages: int = 25,
               delay: float = 0.5, respect_robots: bool = True) -> List[Dict]:
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

            # Define purpose
            purpose_text = """
            Chercher et identifier des informations financières et patrimoniales pertinentes pour le suivi de sociétés cotées,
            communiqués de presse, rapports annuels, transactions importantes, actualité boursière internationale,
            données immobilières et produits financiers. L'objectif est de faciliter la veille pour Le Revenu.
            """

            # print(text)
            result = ai_match_result(seed, resp.url, title, text, purpose_text)
            if result:
                results.append(result)

            pages_processed += 1

            if depth < max_depth:
                for link in links:
                    if same_domain(link, seed) and link not in visited:
                        q.append((link, depth + 1))
        except Exception:
            continue

    return results
