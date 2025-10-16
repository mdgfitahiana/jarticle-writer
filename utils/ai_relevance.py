# utils/ai_relevance.py

import re
import streamlit as st
from typing import List

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import SystemMessage, HumanMessage
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP

# --- LLMs and Embeddings ---
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=st.secrets["OPENAI_API_KEY"],
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=st.secrets["OPENAI_API_KEY"],
)

# --- Text splitter ---
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE,
    separators=["\n\n", "\n", ".", "!", "?", ",", " "],
    chunk_overlap=CHUNK_OVERLAP,
)

# --- Preprocessing ---
def preprocess_text(text: str):
    """
    Normalize + split text into chunks.
    """
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text_splitter.split_text(text)

# --- Build FAISS retriever ---
def build_retriever(chunks: List[str]):
    """
    Turn chunks into FAISS retriever.
    """
    vectorstore = FAISS.from_texts(chunks, embeddings)
    return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 5})

# --- Relevance check with RAG ---
def check_relevance_with_ai(text: str, purpose: str) -> bool:
    """
    Full RAG: 
    1. Split + embed text into retriever
    2. Retrieve relevant chunks
    3. Ask GPT with retrieved context
    """
    chunks = preprocess_text(text)
    if not chunks:
        return False

    retriever = build_retriever(chunks)

    # Retrieve top chunks for purpose
    docs = retriever.get_relevant_documents(purpose)
    if not docs:
        return False









############## prompt



    system_prompt = SystemMessage(
        content=f"""
        Tu es un assistant qui évalue la pertinence d'un texte pour la collecte d'informations financières, patrimoniales et économiques.

        Critères de pertinence :
        - si le texte contient des chiffres clés, données chiffrées ou analyses issues d’un rapport financier ou d’un résultat financier
        - si le texte correspond à un communiqué de presse officiel ou à une annonce publique d’entreprise
        - si le texte évoque une actualité de l’entreprise (changements de direction, acquisitions, partenariats, décisions stratégiques…)
        - si le texte traite d’un investissement en bourse, d’un placement financier (investissement hors bourse) ou d’un investissement immobilier
        - si le texte contient des informations relatives aux impôts, à la fiscalité, à la succession ou à la donation
        - si le texte présente une analyse ou un rapport financier, même partiel

        Sinon, il n’est pas pertinent.

        Réponds uniquement par "oui" ou "non".
        """
    )

    user_prompt = HumanMessage(
        content=f"""
        Contexte de recherche : {purpose}

        Voici les extraits de texte retrouvés :
        {chr(10).join([d.page_content for d in docs])}

        Question : Ce texte est-il pertinent ?
        Réponds uniquement par "oui" ou "non".
        """
    )

    try:
        response = llm.invoke([system_prompt, user_prompt])
        answer = response.content.strip().lower()
        print(f"{docs[0].page_content[:300]} =>", answer)  # debug

        return "oui" in answer or "Oui" in answer
    except Exception as e:
        print("[AI ERROR]", e)
        return FalseR
