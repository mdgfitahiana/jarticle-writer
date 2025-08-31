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
from veille_finance.nlp.extractor import extract_core_sentences


st.set_page_config(page_title="Veille auto", layout="wide")

st.title("Veille financiere automatisée — CRAWLING")

with st.sidebar:
    st.header("Paramètres de crawl")
    max_depth = st.slider("Profondeur (0 = page d'accueil seulement)", 0, 3, 1)
    max_pages = st.slider("Pages max par site", 1, 100, 25)
    delay = st.number_input("Délai entre requêtes (s)", 0.0, 5.0, 0.5, 0.1)
    respect_robots = st.checkbox("Respecter robots.txt du site", value=True)

sheet_url = st.text_input("Colle l'URL du Google Sheet")

if st.button("Lancer le crawl"):
    if not sheet_url:
        st.error("⚠️ Merci de fournir l'URL.")
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

            all_results, prog, status = [], st.progress(0), st.empty()

            for i, seed in enumerate(urls, start=1):
                status.info(f"Crawling {i}/{len(urls)} — {seed}")
                with st.spinner(f"Exploration de {seed} …"):
                    crawl_results = crawl_site(seed, [], max_depth, max_pages, delay, respect_robots)

                    # NEW: post-process each crawled page
                    for r in crawl_results:
                        if "content" in r and r["content"]:
                            r["core_sentences"] = extract_core_sentences(r["content"])
                    all_results.extend(crawl_results)
                prog.progress(int(i/len(urls)*100))

            status.empty(); prog.empty()

            if not all_results:
                st.info("Aucun résultat trouvé.")
            else:
                st.subheader("Pages explorées")
                df_res = pd.DataFrame(all_results)
                display_cols = ["seed", "url", "title", "core_sentences"]
                st.dataframe(df_res[display_cols].fillna(""), use_container_width=True)
                st.download_button("Télécharger résultats", df_res.to_csv(index=False).encode("utf-8"),
                                   "crawl_results.csv", "text/csv")

            st.success("Crawl terminé.")
