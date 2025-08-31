from typing import Set
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag

def extract_text_and_links(html: str, base_url: str) -> (str, Set, str):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("javascript:", "mailto:")):
            continue
        full = urljoin(base_url, href)
        full, _ = urldefrag(full)
        if full.startswith("http"):
            links.add(full)
    return text, links, title
