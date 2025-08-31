import re
import streamlit as st
from typing import List
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.text_splitter import RecursiveCharacterTextSplitter

from veille_finance.config import CHUNK_SIZE, CHUNK_OVERLAP

# Initialize LangChain's OpenAI wrapper
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=st.secrets["OPENAI_API_KEY"]
)

text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            separators=["\n\n", "\n", ".", "!", "?", ",", " "],
            chunk_overlap=CHUNK_OVERLAP,
        )


def preprocess_text(text: str, chunk_size: int = 2000) -> List[str]:
    """
    Split text into manageable chunks and lowercase it.
    """
    text = re.sub(r"\s+", " ", text).strip().lower()
    chunks = text_splitter.split_text(text)
    return chunks

def check_relevance_with_ai(text: str, purpose: str) -> bool:
    """
    Use OpenAI via LangChain to decide if a page is relevant for the usecase.
    
    purpose: a French text describing the information need
    """
    chunks = preprocess_text(text)
    for chunk in chunks:
        prompt = f"""
        Contexte : {purpose}

        Texte extrait d'une page web : 
        \"\"\"{chunk}\"\"\"

        Question : Ce texte est-il pertinent pour la collecte d'informations financières et patrimoniales telle que décrite dans le contexte ?
        Répond uniquement par 'oui' ou 'non'.
        """

        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            answer = response.content.strip().lower()
            print(chunk[:120], "... =>", answer)  # shorten debug print

            if "oui" in answer:
                return True
            break
        except Exception as e:
            print("AI error:", e)
            continue
    return False

def ai_match_result(seed: str, url: str, title: str, text: str, purpose: str):
    """
    Wrapper to return a dict similar to previous interface.
    """
    if check_relevance_with_ai(text, purpose):
        snippet = re.sub(r"\s+", " ", text)[:1500]
        return {
            "seed": seed,
            "url": url,
            "title": title,
            "matched_keywords": "AI-Relevant",
            "snippet": snippet
        }
    return None
