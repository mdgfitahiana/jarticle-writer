import streamlit as st
import pandas as pd
from utils.check_for_change import check_for_change

st.set_page_config(page_title="Veille automatique", layout="wide")
st.title("Vérification automatique des articles")

# --- Sidebar for CSV input ---
sheet_url = st.sidebar.text_input(
    "Colle l'URL du Google Sheet (CSV avec URLs en première colonne)",
    value=""
)

max_depth = st.sidebar.slider("Profondeur du crawl", 0, 20, 10)
max_pages = st.sidebar.slider("Pages max par site", 1, 100, 25)
delay = st.sidebar.number_input("Délai entre requêtes (s)", 0.0, 5.0, 0.5, 0.1)
respect_robots = st.sidebar.checkbox("Respecter robots.txt", value=True)

# --- Load URLs ---
if st.sidebar.button("Lancer la vérification"):
    if not sheet_url:
        st.sidebar.error("⚠️ Merci de fournir l'URL du Google Sheet")
    else:
        try:
            df_urls = pd.read_csv(sheet_url)
            urls = df_urls.iloc[:, 0].dropna().astype(str).tolist()
        except Exception as e:
            st.error(f"Erreur lecture Google Sheet : {e}")
            urls = []

        if not urls:
            st.info("Aucune URL valide trouvée.")
        else:
            # Placeholder table
            table_placeholder = st.empty()
            resources_accum = []

            for i, url in enumerate(urls, start=1):
                with st.spinner(f"Vérification de l'URL {i}/{len(urls)} : {url}"):
                    changed_resources = check_for_change(
                        url,
                        max_depth=max_depth,
                        max_pages=max_pages,
                        delay=delay,
                        respect_robots=respect_robots,
                        output_bool=False  # get changed resources
                    )
                    for r in changed_resources:
                            st.toast(f"Changement détecté : {r['url']}")

                    # Accumulate resources
                    resources_accum.extend(changed_resources)

                    # Convert to DataFrame for display
                    if resources_accum:
                        df_display = pd.DataFrame(resources_accum)
                        # Keep relevant columns for table
                        cols_to_show = ["seed", "url", "title", "snippet"]
                        df_display = df_display[cols_to_show].fillna("")
                        table_placeholder.dataframe(df_display, use_container_width=True)
                    else:
                        table_placeholder.info("Aucun changement détecté pour l'instant.")
