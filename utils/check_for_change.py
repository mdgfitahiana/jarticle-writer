# utils/check_for_change.py

import streamlit as st
from typing import List, Dict, Union
from utils.hash_utils import compute_hash
from crawler.crawler import crawl_site

# ------------------------------------------------------------------------------
# CACHE KEYS
# ------------------------------------------------------------------------------
SOURCES_KEY = "sources"   # Stores n-1 page URLs + their hashes
RESOURCES_KEY = "resources"  # Stores crawler results (PDF + HTML info)

# ------------------------------------------------------------------------------
# MAIN FUNCTION
# ------------------------------------------------------------------------------
def check_for_change(seed_url: str, max_depth: int = 1, max_pages: int = 25,
                     delay: float = 0.5, respect_robots: bool = True,
                     output_bool: bool = True) -> Union[bool, List[Dict]]:
    """
    Check for changes in PDF source pages (n-1 pages).

    Parameters:
    - seed_url: starting URL for crawling
    - max_depth, max_pages, delay, respect_robots: passed to crawler
    - output_bool: if True, return True/False for any change; if False, return list of changed resources

    Returns:
    - True/False if any change detected (default)
    - OR list of changed resources if output_bool=False
    """

    # Load persistent cache
    sources: Dict[str, str] = st.cache_data.get(SOURCES_KEY, {})
    resources: List[Dict] = st.cache_data.get(RESOURCES_KEY, [])

    changes_detected = False
    changed_resources: List[Dict] = []

    # Step 1: If resources empty, run crawler
    if not resources:
        print("[CHECK] Running crawler to initialize resources")
        resources = crawl_site(seed_url, max_depth=max_depth, max_pages=max_pages,
                               delay=delay, respect_robots=respect_robots)
        st.cache_data[SOURCES_KEY] = {}
        st.cache_data[RESOURCES_KEY] = resources

    # Step 2: Initialize sources if empty
    if not sources:
        print("[CHECK] Initializing sources (n-1 pages)")
        sources = {}
        for r in resources:
            pdf_info = r.get("pdf_source", {})
            for parent_url in pdf_info.get("parent_urls", []):
                if parent_url not in sources:
                    sources[parent_url] = ""  # placeholder for hash
        st.cache_data[SOURCES_KEY] = sources

    # Step 3: Compute new hashes for n-1 pages and detect changes
    for parent_url in sources:
        try:
            current_hash = compute_hash(parent_url)
        except Exception as e:
            print(f"[ERROR] Could not fetch or hash page {parent_url}: {e}")
            current_hash = ""

        # Compare with previous hash
        previous_hash = sources.get(parent_url, "")
        if previous_hash != current_hash:
            print(f"[CHANGE] Page changed or new: {parent_url}")
            changes_detected = True
            sources[parent_url] = current_hash  # update hash

            # Collect changed resources if requested
            if not output_bool:
                for r in resources:
                    pdf_info = r.get("pdf_source", {})
                    if parent_url in pdf_info.get("parent_urls", []):
                        changed_resources.append(r)

    # Step 4: Persist updated sources and resources
    st.cache_data[SOURCES_KEY] = sources
    st.cache_data[RESOURCES_KEY] = resources

    return changes_detected if output_bool else changed_resources
