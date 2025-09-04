# utils/parsing.py

from io import BytesIO
from typing import Tuple, List
from bs4 import BeautifulSoup
import fitz  # PyMuPDF


def extract_text_and_links(html: str, base_url: str) -> Tuple[str, List[str], str]:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(" ", strip=True)
    links = [a.get("href") for a in soup.find_all("a", href=True)]
    title = soup.title.string.strip() if soup.title else ""
    return text, links, title


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF bytes using PyMuPDF (fitz).
    Returns extracted text as a string.
    """
    try:
        text_parts = []
        with fitz.open(stream=BytesIO(pdf_bytes), filetype="pdf") as doc:
            for page in doc:
                text_parts.append(page.get_text("text"))  # "text" preserves layout better
        return " ".join(text_parts).strip()
    except Exception as e:
        return f"[PDF parsing error: {e}]"
