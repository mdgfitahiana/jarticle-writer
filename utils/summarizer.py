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

def extract_financial_sentences(text: str) -> list[str]:
    """
    Retourne uniquement les phrases contenant des informations financières,
    actualités ou communiqués pertinents.
    """
    keywords = [
        # Finance / Comptabilité
        "résultat", "bilan", "chiffre", "profit", "perte", "croissance",
        "CA", "revenu", "recette", "dépense", "bénéfice", "dividende",
        "marge", "excédent", "déficit", "capitalisation", "valorisation",
        "milliard", "million", "trimestre", "exercice", "financier",

        # Actualités / Entreprise
        "nomination", "directeur", "PDG", "CEO", "président", "gouvernance",
        "partenariat", "contrat", "lancement", "innovation", "stratégie",
        "plan", "développement", "extension", "croissance externe",

        # Fusions / Acquisitions
        "acquisition", "fusion", "rachat", "cession", "prise de participation",
        "joint-venture", "alliance",

        # Marché / Investissements
        "investissement", "levée de fonds", "financement", "obligation",
        "action", "bourse", "coté", "IPO", "introduction en bourse",
        "émission", "titres", "portefeuille",

        # Rapports / Documents
        "rapport", "communiqué", "publication", "déclaration", "présentation",
        "note d'information", "document d’enregistrement", "URD", "prospectus",
        "analyse", "compte rendu",

        # Contexte macro / Risques
        "inflation", "taux d’intérêt", "marché", "économie", "conjoncture",
        "risque", "réglementaire", "compliance"
    ]
    sentences = re.split(r'(?<=[.!?])\s+', text)
    return [s for s in sentences if any(k.lower() in s.lower() for k in keywords)]


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
    filtered_sentences = extract_financial_sentences(text)
    filtered_text = " ".join(filtered_sentences)
    # comment the next line if needed
    chunks = preprocess_text(filtered_text)

    if not chunks:
        return ""

    retriever = build_retriever(chunks)
    docs = retriever.get_relevant_documents("résumé du contenu")

    if not docs:
        return ""















######################## prompt





    system_prompt = SystemMessage(
        content="""
        Tu es un assistant spécialisé en analyse financière.

        Ta tâche est de produire un résumé clair, structuré et fluide sous forme de texte continu (pas de puces ni de listes).

        Structure le résumé en un ou deux paragraphes :
        - Commence par les actualités importantes : changements de direction, acquisitions, partenariats, décisions stratégiques, ou tout autre événement notable (incluant les rapports financiers, investissements en bourse, placements financiers hors bourse, ou investissements immobiliers).
        - Poursuis avec les résultats et indicateurs financiers clés : bénéfices, revenus, prévisions, dividendes, impôts, et autres données chiffrées pertinentes issues des rapports ou analyses financières.
        - Termine par les éléments officiels et institutionnels : communiqués de presse, rapports publics, annonces réglementaires, ou informations relatives à la succession et à la donation s’il y a lieu.

        Contraintes :
        - Ignore les phrases vagues, génériques ou promotionnelles.
        - Ne conserve que les faits datés, chiffrés ou documentés.
        - Adopte un style journalistique professionnel, concis et objectif.
        """
    )

    user_prompt = HumanMessage(
        content=f"""
        Résume le contenu suivant en suivant les consignes ci-dessus:
        {chr(10).join([d.page_content for d in docs])}
        """
    )

    try:
        response = llm_summarizer.invoke([system_prompt, user_prompt])
        return response.content.strip()


        return summary
    except Exception as e:
        return f"[Error summarizing content: {e}]"