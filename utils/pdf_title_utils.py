# utils/pdf_title_utils.py

from typing import List, Optional
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter
import streamlit as st
import re

try:
    # pypdf >= 3.x
    from pypdf import PdfReader
except Exception:
    # fallback for older environments using PyPDF2
    from PyPDF2 import PdfReader  # type: ignore


# LLM initialization for title extraction (French)
llm_title_extractor = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=st.secrets["OPENAI_API_KEY"]
)


def _clean_lines(text: str) -> List[str]:
    """
    Split text into lines, trim, and filter out obvious noise.
    """
    # Normalize weird spaces
    text = re.sub(r"[ \t]+", " ", text)
    # Replace multiple newlines with single newline to avoid tons of blanks
    text = re.sub(r"\n{2,}", "\n", text)

    lines = [l.strip() for l in text.split("\n")]
    cleaned = []
    for l in lines:
        if not l:
            continue
        # Drop page markers & boilerplate
        if re.search(r"^page\s*\d+\s*(/|sur)?\s*\d*$", l, flags=re.I):
            continue
        if re.search(r"^table\s+des\s+mati[eè]res$", l, flags=re.I):
            continue
        if re.search(r"^confidentiel|^draft|^version\s*\d+", l, flags=re.I):
            # keep possibly, but usually not the main title
            pass
        cleaned.append(l)
    return cleaned


def _score_as_title(line: str) -> float:
    """
    Heuristic score to rank a line as a potential title.
    Higher is better.
    """
    length = len(line)
    # Reasonable title length
    if length < 6 or length > 160:
        return 0.0

    # Penalize lines that clearly look like sentences with trailing punctuation
    ends_with_period = line.endswith(".")
    score = 1.0 - (0.3 if ends_with_period else 0.0)

    # Prefer Title Case or Capitalized Words (common in titles)
    words = line.split()
    cap_words = sum(1 for w in words if re.match(r"^[A-ZÉÈÀÂÎÔÙÇ].*", w))
    ratio_caps = cap_words / max(1, len(words))
    score += 0.4 * ratio_caps

    # Prefer lines without colon (often subtitles) but don't eliminate
    if ":" in line:
        score -= 0.15

    # Bonus if no year/month/day numbers dominate (often subtitles or dates)
    digits = sum(c.isdigit() for c in line)
    if digits > 0:
        score -= 0.1

    # Light bonus for not being ALL CAPS (screaming headers)
    if line.isupper():
        score -= 0.2

    # Clamp
    return max(0.0, min(1.5, score))


def _choose_best_candidate(lines: List[str]) -> Optional[str]:
    """
    Rank lines and return the best candidate.
    """
    if not lines:
        return None
    scored = sorted(((ln, _score_as_title(ln)) for ln in lines), key=lambda x: x[1], reverse=True)
    best, best_score = scored[0]
    # Require a minimal threshold to avoid junk
    return best if best_score >= 0.45 else None


def _extract_text_first_pages(reader: PdfReader, max_pages: int = 3) -> str:
    """
    Extract raw text from the first `max_pages` pages.
    """
    texts = []
    for i, page in enumerate(reader.pages[:max_pages]):
        try:
            txt = page.extract_text() or ""
            texts.append(txt)
        except Exception:
            continue
    return "\n".join(texts).strip()


def _get_title_from_metadata(reader: PdfReader) -> Optional[str]:
    """
    Try PDF metadata title first.
    """
    meta = getattr(reader, "metadata", None) or getattr(reader, "documentInfo", None)
    if not meta:
        return None

    # pypdf uses keys like /Title; PdfReader.metadata.title is normalized on newer versions
    title = None
    if hasattr(meta, "title") and meta.title:
        title = str(meta.title).strip()
    elif isinstance(meta, dict):
        raw = meta.get("/Title") or meta.get("Title")
        title = str(raw).strip() if raw else None

    if title:
        # Filter out placeholders like "untitled", "document"
        if re.fullmatch(r"(?i)untitled|sans\s*titre|document|new document", title):
            return None
        return title
    return None


def _get_title_with_llm(full_text: str) -> Optional[str]:
    """
    LLM-based title extraction on the first pages' text (French).
    Returns None if not confident.
    """
    if not full_text:
        return None

    # Keep the prompt compact and deterministic
    prompt = f"""
Vous êtes un assistant pour des documents financiers et d'entreprise.
Trouvez le **titre principal** du document ci-dessous (tel qu'il apparaîtrait en couverture ou en tête de première page).
Répondez uniquement par le titre exact, sans guillemets, sans majuscules forcées, et sans ajout.
Si vous n'êtes pas sûr, répondez exactement : Non trouvé.

Texte des premières pages :
\"\"\"{full_text[:8000]}\"\"\"
"""
    try:
        response = llm_title_extractor.invoke([HumanMessage(content=prompt)])
        title = (response.content or "").strip()
        if title and title != "Non trouvé" and 5 <= len(title) <= 160:
            # Avoid returning lines that look like a sentence rather than a title
            if _score_as_title(title) >= 0.45:
                return title
    except Exception:
        pass
    return None


def get_title_from_pdf_bytes(pdf_bytes: bytes, max_pages: int = 3) -> str:
    """
    Extract the main title from a PDF (only the first `max_pages` are inspected).
    Order of attempts:
      1) PDF metadata title
      2) Heuristic from early text lines
      3) LLM fallback (French)
    Returns a string, or "Non trouvé".
    """
    try:
        reader = PdfReader(pdf_bytes)
    except Exception:
        return "Non trouvé"

    # 1) Metadata
    meta_title = _get_title_from_metadata(reader)
    if meta_title:
        return meta_title

    # 2) Heuristic on first pages
    early_text = _extract_text_first_pages(reader, max_pages=max_pages)
    lines = _clean_lines(early_text)
    # Only consider the first ~30 lines to focus on the top of the document
    candidate = _choose_best_candidate(lines[:30])
    if candidate:
        return candidate

    # 3) LLM fallback
    llm_title = _get_title_with_llm(early_text)
    if llm_title:
        return llm_title

    return "Non trouvé"


def get_title_from_pdf_path(path: str, max_pages: int = 3) -> str:
    """
    Convenience wrapper to open a PDF by path and use the same logic.
    """
    try:
        with open(path, "rb") as f:
            pdf_bytes = f.read()
        return get_title_from_pdf_bytes(pdf_bytes, max_pages=max_pages)
    except Exception:
        return "Non trouvé"
