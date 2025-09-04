# generate_app.py
import streamlit as st
import urllib.parse

st.set_page_config(page_title="Article Generator", layout="wide")

# Read query params
query_params = st.experimental_get_query_params()

seed = query_params.get("seed", [""])[0]
title = query_params.get("title", [""])[0]
url = query_params.get("url", [""])[0]

st.title("📰 Génération d'article")
st.write("### Paramètres reçus :")
st.json(query_params)

if not url:
    st.warning("⚠️ Aucun paramètre reçu. Merci d’ouvrir cette page depuis le tableau principal.")
else:
    st.success(f"Article demandé pour **{title}** (seed: {seed})")
    st.markdown(f"Lien source : [{url}]({url})")

    # Later: plug your text_generation.generate_article_stream() here
