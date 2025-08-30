from urllib.parse import urlparse

def normalize_url(u: str) -> str:
    u = str(u or "").strip()
    if not u:
        return u
    p = urlparse(u)
    if not p.scheme:
        u = "http://" + u
    return u

def same_domain(a: str, b: str) -> bool:
    na = urlparse(a).netloc.lower().lstrip("www.")
    nb = urlparse(b).netloc.lower().lstrip("www.")
    return na == nb
