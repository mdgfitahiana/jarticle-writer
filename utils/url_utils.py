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

def is_pdf_url(url: str, content_type: str) -> bool:
    """
    Detect whether a URL or response content-type indicates a PDF file.
    - Match if '.pdf' appears anywhere in the URL (including query params).
    - Match if the content-type header includes 'pdf'.
    """
    url_l = url.lower()
    return ".pdf" in url_l or "pdf" in content_type
