# text_generation.py
import streamlit as st
from langchain_openai import ChatOpenAI

def generate_article(seed: str, title: str, financial_result: str, press_release: str) -> str:
    """
    Génère un article financier en français à partir des liens fournis.
    GPT-4o-mini fera de son mieux pour synthétiser le contenu des pages et PDF.
    
    Args:
        seed (str): Source originale (métadonnée)
        title (str): Titre de l'entrée
        financial_result (str): URL des résultats financiers
        press_release (str): URL du communiqué de presse

    Returns:
        str: Texte de l'article généré
    """

    # Nettoyage des liens
    links = [link.strip() for link in [financial_result, press_release] if isinstance(link, str) and link.strip()]
    if not links:
        return "⚠️ Aucun lien valide trouvé pour générer l'article."

    # Init LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    # Prompt en français
    prompt = f"""
    Vous êtes un journaliste financier professionnel.
    Votre tâche est de rédiger un article synthétique et clair sur l'entreprise,
    en utilisant uniquement les informations disponibles dans les liens suivants :
    
    {links}
    
    Instructions :
    - Utilisez uniquement ces liens.
    - Si un lien est un PDF, synthétisez-en les informations pertinentes.
    - Concentrez-vous sur les chiffres clés, résultats financiers et informations du communiqué de presse.
    - Écrivez l'article en français, dans un style professionnel et journalistique.
    - Ne faites aucune recherche externe.
    """

    try:
        response = llm.invoke(prompt)
        return response.content.strip()
    except Exception as e:
        return f"⚠️ Erreur génération article : {e}"
