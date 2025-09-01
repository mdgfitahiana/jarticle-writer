import streamlit as st
import markdown2
import pandas as pd
from text_generation import generate_article
from weasyprint import HTML
st.set_page_config(page_title="Veille auto", layout="wide")

# --- Sidebar ---
st.sidebar.header("Paramètres de génération")

# Download format selection
download_format = st.sidebar.radio(
    "Format de téléchargement",
    ("TXT", "PDF"),
    index=0
)

# Google Sheet URL input
# app.py snippet
sheet_url = st.sidebar.text_input(
    "Colle l'URL du Google Sheet",
    value=st.secrets.get("CSV_URL", "")
)

# --- Session state initialization ---
if "df" not in st.session_state:
    st.session_state.df = None
if "selected_title" not in st.session_state:
    st.session_state.selected_title = None
if "generated_article" not in st.session_state:
    st.session_state.generated_article = None

# --- Welcome message ---
if st.session_state.df is None:
    st.title("Bienvenue dans Veille Financière Automatisée")
    st.write(
        "Collez l'URL de votre Google Sheet dans la barre latérale, "
        "choisissez le format de téléchargement, puis cliquez sur 'Obtenir la liste' pour commencer."
    )

# --- Step 1: Load CSV ---
if st.sidebar.button("Obtenir la liste"):
    if not sheet_url:
        st.sidebar.error("⚠️ Merci de fournir l'URL.")
    else:
        try:
            df = pd.read_csv(sheet_url)
            expected_cols = {"seed", "title", "financial-result", "press-release"}
            if not expected_cols.issubset(df.columns):
                st.sidebar.error(f"⚠️ Le fichier CSV doit contenir les colonnes {expected_cols}")
            else:
                st.session_state.df = df
                st.session_state.generated_article = None
                st.success(f"{len(df)} entrées détectées.")
        except Exception as e:
            st.sidebar.error(f"Erreur lecture Google Sheet : {e}")

# --- Step 2: Main content ---
if st.session_state.df is not None:
    st.subheader("Choisir une entrée")
    options = st.session_state.df["title"].dropna().astype(str).tolist()
    st.session_state.selected_title = st.selectbox(
        "Sélectionnez un titre",
        options,
        index=options.index(st.session_state.selected_title)
        if st.session_state.selected_title in options else 0
    )

    selected_row = st.session_state.df[st.session_state.df["title"] == st.session_state.selected_title].iloc[0]

    # --- Step 3: Generate article ---
    if st.button("Générer"):
        with st.spinner("Génération de l'article en cours..."):
            st.session_state.generated_article = generate_article(
                selected_row["seed"],
                selected_row["title"],
                selected_row["financial-result"],
                selected_row["press-release"]
            )

    # --- Step 4: Display and download ---
    if st.session_state.generated_article:
        st.subheader("Article généré")
        st.write(st.session_state.generated_article)

        # Download logic
        if download_format == "TXT":
            st.download_button(
                "Télécharger l'article (TXT)",
                st.session_state.generated_article.encode("utf-8"),
                "article.txt",
                "text/plain"
            )
        else:  # PDF
            # Convert markdown text to HTML
            html = markdown2.markdown(st.session_state.generated_article)
            # Generate PDF bytes
            pdf_bytes = HTML(string=html).write_pdf()
            st.download_button(
                "Télécharger l'article (PDF)",
                pdf_bytes,
                "article.pdf",
                "application/pdf"
            )
