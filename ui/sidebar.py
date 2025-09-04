import streamlit as st

def render_sidebar(default_download_format="TXT", sheet_url_secret_key="CSV_URL"):
    st.sidebar.header("Paramètres de génération")

    # Download format selection
    if "download_format" not in st.session_state:
        st.session_state.download_format = default_download_format

    st.session_state.download_format = st.sidebar.radio(
        "Format de téléchargement",
        ("TXT", "PDF"),
        index=0 if st.session_state.download_format == "TXT" else 1
    )

    # Google Sheet URL input
    sheet_url = st.sidebar.text_input(
        "Colle l'URL du Google Sheet",
        value=st.secrets.get(sheet_url_secret_key, "")
    )

    # --- Crawl parameters ---
    st.sidebar.header("Paramètres de crawl")
    max_depth = st.sidebar.slider(
        "Profondeur (0 = page d'accueil seulement)", 0, 20, 5
    )
    max_pages = st.sidebar.slider(
        "Pages max par site", 1, 100, 25
    )
    delay = st.sidebar.number_input(
        "Délai entre requêtes (s)", 0.0, 5.0, 0.5, 0.1
    )
    respect_robots = st.sidebar.checkbox(
        "Respecter robots.txt du site", value=True
    )

    return {
        "sheet_url": sheet_url,
        "max_depth": max_depth,
        "max_pages": max_pages,
        "delay": delay,
        "respect_robots": respect_robots
    }
