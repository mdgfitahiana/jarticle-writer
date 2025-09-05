# utils/summarize.py

import streamlit as st
import re
from typing import List
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain.schema import SystemMessage, HumanMessage
from langchain.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from utils.ai_relevance import text_splitter  # re-use splitter

# ------------------------------------------------------------------------------
# LLM initialization (separate instance for summarization)
# ------------------------------------------------------------------------------
llm_summarizer = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=st.secrets["OPENAI_API_KEY"]
)

embeddings = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key=st.secrets["OPENAI_API_KEY"]
)

# ------------------------------------------------------------------------------
# Preprocess & chunk text
# ------------------------------------------------------------------------------
def preprocess_text(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    return text_splitter.split_text(text)

# ------------------------------------------------------------------------------
# Build FAISS retriever
# ------------------------------------------------------------------------------
def build_retriever(chunks: List[str]):
    vectorstore = FAISS.from_texts(chunks, embeddings)
    return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": 3})

# ------------------------------------------------------------------------------
# Summarize content using RAG
# ------------------------------------------------------------------------------
def summarize_content(text: str) -> str:
    """
    Summarize the content using a retrieval-augmented LLM workflow.
    Interface unchanged: takes text and returns string summary.
    """
    chunks = preprocess_text(text)
    if not chunks:
        return ""

    retriever = build_retriever(chunks)
    docs = retriever.get_relevant_documents("résumé du contenu")

    if not docs:
        return ""

    system_prompt = SystemMessage(
        content="""
        Tu es un assistant qui résume des textes longs en quelques phrases claires en français.
        Concentre-toi sur les informations clés et ignorer les détails inutiles.
        """
    )

    user_prompt = HumanMessage(
        content=f"""
        Résume le contenu suivant :
        {chr(10).join([d.page_content for d in docs])}
        """
    )

    try:
        response = llm_summarizer.invoke([system_prompt, user_prompt])
        return response.content.strip()
    except Exception as e:
        return f"[Error summarizing content: {e}]"
