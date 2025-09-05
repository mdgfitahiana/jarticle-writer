# app.py
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components

from ui.sidebar import render_sidebar
from utils.check_for_change import check_for_change
from utils.resouce_table import summarize_content
from ui.styles import build_html_table, build_body_rows


st.set_page_config(page_title="Veille Automatisée", layout="wide")
st.title("Veille Financière Automatisée")

# Sidebar
params = render_sidebar()
sheet_url = params["sheet_url"]
max_depth = params["max_depth"]
max_pages = params["max_pages"]
delay = params["delay"]
respect_robots = params["respect_robots"]

# Load Google Sheet
if not sheet_url:
    st.warning("Merci de fournir l'URL du Google Sheet.")
    st.stop()

try:
    df_sheet = pd.read_csv(sheet_url)
    seed_urls = df_sheet.iloc[:, 0].dropna().astype(str).tolist()
except Exception as e:
    st.error(f"Erreur lecture Google Sheet : {e}")
    st.stop()

if not seed_urls:
    st.info("Aucune URL valide détectée dans le sheet.")
    st.stop()

st.success(f"{len(seed_urls)} URL(s) détectées.")

# Collect results
all_resources = []
for i, seed in enumerate(seed_urls, start=1):
    with st.spinner(f"📡 Vérification de l'URL {i}/{len(seed_urls)} : {seed}"):
        changed_resources = check_for_change(
            seed_url=seed,
            output_bool=False,
            max_depth=max_depth,
            max_pages=max_pages,
            delay=delay,
            respect_robots=respect_robots,
        )
    if changed_resources:
        all_resources.extend(changed_resources)
        for r in changed_resources:
            st.toast(f"Changement détecté sur {r['url']}")

st.success("✅ Vérification terminée.")

# Headers
headers = [
    "Liste des entreprises",
    "Type de l'article",
    "Contenu (résumé par IA)",
    "Dernière date de parution",
    "Lien de l'article",
]

# Recent (changed) table
with st.spinner("🖊️ Formatage du tableau des changements récents..."):
    groups_recent = []
    for seed in seed_urls:
        resources_for_seed = [r for r in all_resources if r.get("seed") == seed]
        if resources_for_seed:
            groups_recent.append({
                "label": resources_for_seed[0].get("company_name", seed),
                "rows": resources_for_seed
            })

    if groups_recent:
        body_html_recent = build_body_rows(groups_recent, summarize_content, blink=True)
        table_html_recent = build_html_table(headers, body_html_recent, blink=True)
        st.subheader("🆕 Derniers changements détectés")
        components.html(table_html_recent, height=600, scrolling=True)
    else:
        st.info("Aucun changement récent détecté.")

# Full table
with st.spinner("🖊️ Construction du tableau complet..."):
    groups_full = []
    for seed in seed_urls:
        resources_for_seed = [r for r in all_resources if r.get("seed") == seed]
        if not resources_for_seed:
            resources_for_seed = [{"title": "", "content": "", "last_date": "", "url": ""}]
        groups_full.append({
            "label": resources_for_seed[0].get("company_name", seed),
            "rows": resources_for_seed
        })

    body_html_full = build_body_rows(groups_full, summarize_content, blink=False)
    table_html_full = build_html_table(headers, body_html_full, blink=False)
    st.subheader("📚 Tableau complet des ressources")
    components.html(table_html_full, height=800, scrolling=True)
