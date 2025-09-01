import streamlit as st
import pandas as pd
import markdown2
from text_generation import generate_article_stream
from weasyprint import HTML

st.set_page_config(page_title="Veille auto", layout="wide")

# --- Sidebar ---
st.sidebar.header("Paramètres de génération")

# Download format selection
if "download_format" not in st.session_state:
    st.session_state.download_format = "TXT"

st.session_state.download_format = st.sidebar.radio(
    "Format de téléchargement",
    ("TXT", "PDF"),
    index=0 if st.session_state.download_format == "TXT" else 1
)

# Google Sheet URL input (default from secret)
sheet_url = st.sidebar.text_input(
    "Colle l'URL du Google Sheet",
    value=st.secrets.get("CSV_URL", "")
)

# --- Session state initialization ---
for key in ["df", "selected_title", "generated_article"]:
    if key not in st.session_state:
        st.session_state[key] = None

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
                st.session_state.selected_title = None
                st.success(f"{len(df)} entrées détectées.")
        except Exception as e:
            st.sidebar.error(f"Erreur lecture Google Sheet : {e}")

# --- Step 2: Main content ---
if st.session_state.df is not None:
    st.subheader("Choisir une entrée")
    options = st.session_state.df["title"].dropna().astype(str).tolist()

    # --- Selectbox with change detection ---
    prev_title = st.session_state.selected_title
    st.session_state.selected_title = st.selectbox(
        "Sélectionnez un titre",
        options,
        index=options.index(prev_title) if prev_title in options else 0,
        key="title_select"
    )

    # Clear previous article if selection changed
    if prev_title != st.session_state.selected_title:
        st.session_state.generated_article = None

    selected_row = st.session_state.df[
        st.session_state.df["title"] == st.session_state.selected_title
    ].iloc[0]

    # --- Step 3: Generate article ---
    generate_btn = st.button("Générer")
    article_placeholder = st.empty()

    if generate_btn:
        st.session_state.generated_article = ""

        def on_new_token(token: str):
            st.session_state.generated_article += token
            article_placeholder.markdown(st.session_state.generated_article)

        # Call streaming function
        generate_article_stream(
            selected_row["seed"],
            selected_row["title"],
            selected_row["financial-result"],
            selected_row["press-release"],
            on_new_token
        )

    # --- Step 4: Display and download ---
    if st.session_state.generated_article:
        st.subheader("Article généré")
        article_placeholder.markdown(st.session_state.generated_article)

        if st.session_state.download_format == "TXT":
            st.download_button(
                "Télécharger l'article (TXT)",
                st.session_state.generated_article.encode("utf-8"),
                "article.txt",
                "text/plain"
            )
        else:  # PDF
            html = markdown2.markdown(st.session_state.generated_article)
            pdf_bytes = HTML(string=html).write_pdf()
            st.download_button(
                "Télécharger l'article (PDF)",
                pdf_bytes,
                "article.pdf",
                "application/pdf"
            )
