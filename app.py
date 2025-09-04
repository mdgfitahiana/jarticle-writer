import streamlit as st
import pandas as pd
from ui.sidebar import render_sidebar
from utils.check_for_change import check_for_change

st.set_page_config(page_title="Veille Automatisée", layout="wide")
st.title("Veille Financière Automatisée")

# --- Sidebar parameters ---
params = render_sidebar()
sheet_url = params["sheet_url"]
max_depth = params["max_depth"]
max_pages = params["max_pages"]
delay = params["delay"]
respect_robots = params["respect_robots"]

# --- Load Google Sheet ---
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
    st.info("Aucune URL valide trouvée dans le sheet.")
    st.stop()

st.success(f"{len(seed_urls)} URL(s) détectées.")

# --- Collect results ---
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

# --- Show table once at the end ---
if all_resources:
    df_table = pd.DataFrame(all_resources)
else:
    headers = ["seed", "url", "title", "last_date", "content", "matched_keywords"]
    df_table = pd.DataFrame(columns=headers)

st.subheader("Résumé des ressources")
st.dataframe(df_table.fillna(""), use_container_width=True)

st.success("Vérification terminée pour toutes les URLs.")
