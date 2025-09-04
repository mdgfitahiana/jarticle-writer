# utils/date_utils.py

from bs4 import BeautifulSoup
from datetime import datetime
import requests
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
import streamlit as st
import re
from datetime import datetime

# ------------------------------------------------------------------------------
# LLM initialization for date extraction
# ------------------------------------------------------------------------------
llm_date_extractor = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=st.secrets["OPENAI_API_KEY"]
)

# ------------------------------------------------------------------------------
# AI-based date extraction from text (chunk by chunk, French)
# ------------------------------------------------------------------------------
def get_date_from_text_ai(full_text: str, max_pages: int = 3) -> str:
    """
    Try to extract publication date using AI from text content in French.
    Processes chunks one by one and returns the first valid date found.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200
    )
    chunks = splitter.split_text(full_text)
    relevant_chunks = chunks[:max_pages]

    for i, chunk in enumerate(relevant_chunks, start=1):
        prompt = f"""
Vous êtes un assistant pour des articles financiers. 
Déterminez la date de publication de l'article à partir du texte fourni ci-dessous. 
Répondez uniquement par la date si vous êtes sûr, en format ISO (YYYY-MM-DD). 
Si aucune date précise n'est trouvée, répondez par "Non trouvé".

Texte (partie {i} sur {len(relevant_chunks)}):
\"\"\"{chunk}\"\"\"
"""
        try:
            response = llm_date_extractor.invoke([HumanMessage(content=prompt)])
            date_text = response.content.strip()

            # Quick check: basic ISO date pattern
            if re.match(r"\d{4}-\d{2}-\d{2}", date_text):
                return date_text
        except Exception as e:
            continue  # skip chunk if LLM fails

    return "Non trouvé"

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
