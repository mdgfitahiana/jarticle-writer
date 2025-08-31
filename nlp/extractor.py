# extractor.py
import streamlit as st
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage

# Initialize LLM once
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0,
    api_key=st.secrets["OPENAI_API_KEY"]
)

def extract_core_sentences(text: str, max_sentences: int = 3) -> list[str]:
    """
    Use GPT to extract the most informative sentences from raw text.
    Keeps pronoun resolution context better than rule-based NER.
    """

    prompt = f"""
    Voici un texte extrait d'une page web :

    \"\"\"{text}\"\"\"

    Ta tâche : Extraire les {max_sentences} phrases les plus informatives
    concernant des informations financières ou patrimoniales (entreprises,
    personnes, investissements, argent, patrimoine, marchés, etc.).

    Réponds uniquement avec une liste de phrases exactes issues du texte,
    sans reformuler ni commenter.
    """

    try:
        response = llm.invoke([HumanMessage(content=prompt)])
        sentences = response.content.strip().split("\n")

        # clean bullet points / numbering if GPT adds them
        clean_sentences = [s.lstrip("-•0123456789. ").strip() for s in sentences if s.strip()]

        return clean_sentences[:max_sentences]

    except Exception as e:
        print("Error in extract_core_sentences:", e)
        return []
