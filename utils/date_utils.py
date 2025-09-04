# utils/date_utils.py

from bs4 import BeautifulSoup
from datetime import datetime
import requests

def get_date_from_headers(resp: requests.Response) -> str:
    """
    Try to extract last modified date from HTTP headers.
    Fallback to current UTC datetime if not found.
    """
    last_modified = resp.headers.get("Last-Modified")
    if last_modified:
        return last_modified
    return datetime.utcnow().isoformat()

def get_date_from_html(html_text: str, resp: requests.Response) -> str:
    """
    Try to extract a date from HTML content:
    1. <time datetime="...">
    2. <time>...</time>
    3. <meta name="date" content="...">
    4. fallback to HTTP headers
    """
    soup = BeautifulSoup(html_text, "html.parser")
    
    # 1. <time datetime="...">
    time_tag = soup.find("time")
    if time_tag:
        if time_tag.has_attr("datetime"):
            return time_tag["datetime"]
        text_time = time_tag.get_text(strip=True)
        if text_time:
            return text_time
    
    # 2. <meta name="date" content="...">
    meta_date = soup.find("meta", {"name": "date"})
    if meta_date and meta_date.has_attr("content"):
        return meta_date["content"]

    # 3. fallback to HTTP headers
    return get_date_from_headers(resp)
