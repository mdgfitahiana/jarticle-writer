import streamlit as st
from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage
from langchain.callbacks.base import BaseCallbackHandler

class StreamlitCallbackHandler(BaseCallbackHandler):
    """Custom callback to stream tokens to Streamlit."""
    def __init__(self, on_new_token):
        self.on_new_token = on_new_token

    def on_llm_new_token(self, token: str, **kwargs):
        self.on_new_token(token)

def generate_article_stream(seed: str, title: str, financial_result: str, press_release: str,
                            on_new_token):
    """
    Generates a financial article in French by streaming tokens.
    
    Parameters:
    - seed: str — seed URL (not really used here, kept for interface)
    - title: str — title of the company/entry
    - financial_result: str — link to financial result page/PDF
    - press_release: str — link to press release page/PDF
    - on_new_token: callable — function(token: str) called for every new token
    """

    # Collect the links
    links = [link.strip() for link in [financial_result, press_release]
             if isinstance(link, str) and link.strip()]
    if not links:
        on_new_token("⚠️ Aucun lien valide trouvé pour générer l'article.")
        return

    # Build the prompt in French
    prompt = f"""
Vous êtes un journaliste financier professionnel.
Rédigez un article synthétique et clair sur l'entreprise "{title}",
en utilisant uniquement les informations disponibles dans les liens suivants :
{links}

Instructions :
- Utilisez uniquement ces liens.
- Si un lien est un PDF, synthétisez-en les informations pertinentes.
- Concentrez-vous sur les chiffres clés, résultats financiers et informations du communiqué de presse.
- Écrivez l'article en français, dans un style professionnel et journalistique.
- Ne faites aucune recherche externe.
"""

    # Initialize streaming LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.4,
        streaming=True,
        openai_api_key=st.secrets["OPENAI_API_KEY"]
    )

    # Create callback handler
    callback_handler = StreamlitCallbackHandler(on_new_token)

    # Send prompt as a single HumanMessage
    llm([HumanMessage(content=prompt)], callbacks=[callback_handler])
