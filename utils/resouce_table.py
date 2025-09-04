import streamlit as st
import pandas as pd
from utils.ai_relevance import llm, text_splitter  # re-use your langchain setup
from utils.check_for_change import RESOURCES_KEY

# ------------------------------------------------------------------------------
# LLM initialization (separate instance for summarization)
# ------------------------------------------------------------------------------
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

llm_summarizer = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=st.secrets["OPENAI_API_KEY"]
)

# ------------------------------------------------------------------------------
# Summarize content using LLM
# ------------------------------------------------------------------------------
def summarize_content(text: str) -> str:
    """
    Summarize the content using LLM.
    """
    # Simple split to handle long text
    chunks = text_splitter.split_text(text)
    summary = []
    for chunk in chunks:
        prompt = f"""
        Résume le contenu suivant en quelques phrases claires, en français :
        \"\"\"{chunk}\"\"\"
        """
        try:
            response = llm_summarizer.invoke([HumanMessage(content=prompt)])
            summary.append(response.content.strip())
        except Exception as e:
            summary.append(f"[Error summarizing chunk: {e}]")
    return " ".join(summary)

# ------------------------------------------------------------------------------
# Create resource table for a given URL
# ------------------------------------------------------------------------------
def get_resource_table_for_url(url: str) -> pd.DataFrame:
    """
    Generate a table of resources for a given URL.

    Columns:
    - Liste des entreprises
    - Type de l'article
    - Contenu (résumé par IA)
    - Dernière date de parution
    - Lien de l'article
    - Proposer un article à générer (placeholder link)
    - Article généré (empty for now)
    """
    headers = [
        "Liste des entreprises",
        "Type de l'article",
        "Contenu (résumé par IA)",
        "Dernière date de parution",
        "Lien de l'article",
        "Proposer un article à générer",
        "Article généré"
    ]

    resources = st.cache_data.get(RESOURCES_KEY, [])
    rows = []

    for r in resources:
        # Match by URL or parent URLs
        pdf_info = r.get("pdf_source", {})
        urls_to_match = [r.get("url")] + pdf_info.get("parent_urls", [])
        if url in urls_to_match:
            entreprise = r.get("seed", "")
            article_type = r.get("title", "")
            content = r.get("content", "")
            summary = summarize_content(content) if content else ""
            last_date = r.get("last_date", "")  # if you have this info in crawler
            link = r.get("url", "")
            generate_link = "https://new.tab.com/new/generation"
            article_generated = ""  # placeholder

            rows.append([
                entreprise,
                article_type,
                summary,
                last_date,
                link,
                generate_link,
                article_generated
            ])

    return pd.DataFrame(rows, columns=headers)
