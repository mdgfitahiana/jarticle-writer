import streamlit as st
import pandas as pd
import requests 
from bs4 import BeautifulSoup

results = []

st.set_page_config(page_title="Veille Auto", layout="wide")

st.title("Veille financiere Automatisee")
st.write("Hello ! pour commencer :")
st.markdown("- Entrer un Google Sheet contenant des URLs")
st.markdown("- Entrer les mots-cles a rechercher")
st.markdown("- Puis, lancer le crawling pour voir les resultats")

# Input du lien Google Sheet
sheet_url = st.text_input("Colle l'URL de ton Google Sheet ici")

# Input pour les mots-cles
keywords_input = st.text_input("Entre les mots-clés à chercher (séparés par des virgules)")

# Bouton d'activation du crawling
if st.button("Lancer"):
    if not sheet_url:
        st.error("⚠️ Merci d'entrer l'URL du Google Sheet.")
    elif not keywords_input:
        st.error("⚠️ Merci d'entrer au moins un mot-clé.")
    else:
        try:
            # lecture CSV depuis le Google Sheet
            df = pd.read_csv(sheet_url)

            # Prendre la première colonne et nettoyer les URLs
            urls = (
                df[df.columns[0]]
                .dropna()                 # enlève cellules vides
                .map(str.strip)           # enlève espaces avant/après
                .loc[lambda x: x != ""]   # enlève les chaînes vides
                .tolist()
            )

            st.success(f"Crawling démarré sur {len(urls)} URLs trouvées :")
            
            # Afficher la liste des URLs dans le sheet
            df_urls = pd.DataFrame({"URL": urls})
            st.subheader("Les URLs du Sheet sont : ")
            st.table(df_urls)

            # Recherche mots-clés
            st.subheader("Recherche des mots-clés sur chaque URL")
            keywords = [kw.strip().lower() for kw in keywords_input.split(",") if kw.strip()]
            results = []

            for url in urls:
                try:
                    resp = requests.get(url, timeout=5)
                    soup = BeautifulSoup(resp.text, "html.parser")
                    text = soup.get_text().lower()

                    found = [kw for kw in keywords if kw in text]
                    if found:
                        results.append({"URL": url, "Mots trouvés": ", ".join(found)})
                except Exception as e:
                    results.append({"URL": url, "Mots trouvés": f"Erreur: {e}"})

            # Affichage des résultats
            if results:
                st.subheader("Les URLs contenant vos mots-clés :")
                st.table(pd.DataFrame(results))
            else:
                st.info("Aucun mot-clé trouvé dans ces URLs.")

        except Exception as e:
            st.error(f"Impossible de lire le Google Sheet : {e}")