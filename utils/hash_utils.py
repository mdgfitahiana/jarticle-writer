import hashlib

def compute_page_hash(html_content: str) -> str:
    """
    Compute a SHA-256 hash of the given HTML content.
    This can be used to detect if a page has changed.
    
    Args:
        html_content (str): The full HTML/text content of the page.

    Returns:
        str: The hexadecimal hash string.
    """
    if not html_content:
        return ""
    
    # Ensure consistent encoding
    content_bytes = html_content.encode("utf-8")
    hash_object = hashlib.sha256(content_bytes)
    return hash_object.hexdigest()
