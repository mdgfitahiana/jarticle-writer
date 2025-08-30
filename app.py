import os, sys

# get the absolute path of the parent directory (project root)
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))  
PARENT_DIR = os.path.dirname(ROOT_DIR)

# add parent dir to sys.path if not already there
if PARENT_DIR not in sys.path:
    sys.path.insert(0, PARENT_DIR)


import streamlit as st
import pandas as pd
from veille_finance.crawler.crawler import crawl_site

st.set_page_config(page_title="Veille auto", layout="wide")

st.title("Veille financiere automatisée — CRAWLING")

with st.sidebar:
    st.header("Paramètres de crawl")
    max_depth = st.slider("Profondeur (0 = page d'accueil seulement)", 0, 3, 1)
    max_pages = st.slider("Pages max par site", 1, 100, 25)
    delay = st.number_input("Délai entre requêtes (s)", 0.0, 5.0, 0.5, 0.1)
    respect_robots = st.checkbox("Respecter robots.txt du site", value=True)
    show_snippet = st.checkbox("Afficher un extrait (snippet)", value=True)

sheet_url = st.text_input("Colle l'URL du Google Sheet")
keywords_input = st.text_input("Mots-clés (séparés par des virgules)")

if st.button("Lancer le crawl"):
    if not sheet_url or not keywords_input:
        st.error("⚠️ Merci de fournir l'URL et des mots-clés.")
    else:
        try:
            df = pd.read_csv(sheet_url)
            urls = df.iloc[:,0].dropna().astype(str).str.strip()
            urls = [u for u in urls if u]
        except Exception as e:
            st.error(f"Erreur lecture Google Sheet : {e}")
            urls = []

        if not urls:
            st.info("Aucune URL valide trouvée.")
        else:
            st.success(f"{len(urls)} site(s) à crawler.")
            st.table(pd.DataFrame({"URL": urls}))

            keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
            all_results, prog, status = [], st.progress(0), st.empty()

            for i, seed in enumerate(urls, start=1):
                status.info(f"Crawling {i}/{len(urls)} — {seed}")
                with st.spinner(f"Exploration de {seed} …"):
                    all_results.extend(crawl_site(seed, keywords, max_depth, max_pages, delay, respect_robots))
                prog.progress(int(i/len(urls)*100))

            status.empty(); prog.empty()

            if not all_results:
                st.info("Aucun mot-clé trouvé.")
            else:
                st.subheader("Pages contenant des mots-clés")
                df_res = pd.DataFrame(all_results)
                display_cols = ["seed", "url", "title", "matched_keywords"]
                if show_snippet: display_cols.append("snippet")
                st.dataframe(df_res[display_cols].fillna(""), use_container_width=True)
                st.download_button("Télécharger résultats", df_res.to_csv(index=False).encode("utf-8"),
                                   "crawl_results.csv", "text/csv")

            st.success("Crawl terminé.")
