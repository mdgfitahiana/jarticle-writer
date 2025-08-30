import time
import re
from collections import deque #structure file (FIFO)
from urllib.parse import urljoin, urlparse, urldefrag

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import urllib.robotparser as robotparser

##################### CONFIGURATION #####################

st.set_page_config(page_title="Veille auto", layout="wide")

HEADERS = {"User-Agent": "VeilleBot/0.1 (+mailto:missah@ohatra.com)"}

DEFAULT_TIMEOUT = 10

##################### UTILITAIRES POUR URL ET robots.txt #####################

#S'assurer que la chaine est propre et ajoute http:// au cas oU
def normalize_url(u: str) -> str:
    u = str(u or "").strip()
    if not u:
        return u
    p = urlparse(u)
    if not p.scheme:
        u = "http://" + u
    return u

#Verifier si deux URLs appartiennent au meme site
def same_domain(a: str, b: str) -> bool:
    na = urlparse(a).netloc.lower().lstrip("www.")
    nb = urlparse(b).netloc.lower().lstrip("www.")
    return na == nb

#Mettre en cache le resultat du parsing de robots.txt pour ne pas le lire à chaque page
_robot_cache: dict = {}
def get_robot_parser_for(url: str):
    parsed = urlparse(url)
    base = f"{parsed.scheme}://{parsed.netloc}"
    if base in _robot_cache:
        return _robot_cache[base]
    rp = robotparser.RobotFileParser()
    try:
        rp.set_url(base + "/robots.txt")
        rp.read()
        _robot_cache[base] = rp
    except Exception:
        _robot_cache[base] = None
    return _robot_cache[base]

#Savoir si on peut recuperer la page
def allowed_by_robots(url: str) -> bool:
    rp = get_robot_parser_for(url)
    if not rp:
        return True
    try:
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return True

#####################  EXTRACTION DE TEXTES ET LIENS ##################### 

#Parser le html et recuperer le lien, le titre et le texte
def extract_text_and_links(html: str, base_url: str):
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(" ")
    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith("javascript:") or href.startswith("mailto:"):
            continue
        full = urljoin(base_url, href)
        full, _ = urldefrag(full)
        if full.startswith("http"):
            links.add(full)
    return text, links, title

##################### CRAWLING (BFS limité) #####################

#Explorer les pages a partir d'un seed_url (=page principale) en respectant robots.txt
def crawl_site(seed_url: str, keywords: list, max_depth: int = 1, max_pages: int = 25,
               delay: float = 0.5, respect_robots: bool = True):
    seed = normalize_url(seed_url)
    results = []
    visited = set() #pour eviter de revisiter les liens
    q = deque([(seed, 0)])
    pages_processed = 0

    while q and pages_processed < max_pages:
        url, depth = q.popleft()
        if url in visited:
            continue
        visited.add(url)

        if respect_robots and not allowed_by_robots(url):
            # ignoré si pas d'accès
            continue

        # pause courte avant chaque requête
        if delay > 0:
            time.sleep(delay)

        try:
            resp = requests.get(url, headers=HEADERS, timeout=DEFAULT_TIMEOUT)
            if not resp.ok:
                continue
            ct = resp.headers.get("Content-Type", "").lower()
            if "html" not in ct:
                continue

            text, links, title = extract_text_and_links(resp.text, resp.url)
            ltext = (text or "").lower()
            lurl = (resp.url or "").lower()

            matched = []
            for kw in keywords:
                k = kw.lower()
                if k in ltext or k in lurl:
                    matched.append(kw)

            if matched:
                #tronquer le texte en un snippet de 300 car max (extrait)
                snippet = re.sub(r"\s+", " ", ltext)
                snippet = snippet[:1500] if len(snippet) > 1500 else snippet
                results.append({
                    "seed": seed,
                    "url": resp.url,
                    "title": title,
                    "matched_keywords": ", ".join(sorted(set(matched), key=str.lower)),
                    "snippet": snippet
                })

            pages_processed += 1

            # file d'attente des liens du meme domaine
            if depth < max_depth:
                for link in links:
                    if same_domain(link, seed) and link not in visited:
                        q.append((link, depth + 1))

        except Exception:
            # ignorer les erreurs de page individuelles (timeout, connection, parse...)
            continue

    return results

##################### INTERFACE + Paramètres du crawling #####################

st.title("Veille financiere automatisée — CRAWLING")
st.write("Entrez le lien du Google Sheet contenant les liens a crawler, les mots-clés, puis lance le crawl.")

with st.sidebar:
    st.header("Paramètres de crawl")
    max_depth = st.slider("Profondeur (0 = page d'accueil seulement)", 0, 3, 1)
    max_pages = st.slider("Pages max par site", 1, 100, 25)
    delay = st.number_input("Délai entre requêtes (s)", min_value=0.0, max_value=5.0, value=0.5, step=0.1)
    respect_robots = st.checkbox("Respecter robots.txt du site", value=True)
    show_snippet = st.checkbox("Afficher un extrait (snippet) de texte correspondant aux mots-clés", value=True)

##################### INPUTS #####################

sheet_url = st.text_input("Colle l'URL de ton Google Sheet")
keywords_input = st.text_input("Mots-clés ( séparés par des virgules)")

##################### LANCER #####################

if st.button("Lancer le crawl"):
    if not sheet_url:
        st.error("⚠️ Merci d'entrer l'URL du Google Sheet.")
    elif not keywords_input:
        st.error("⚠️ Merci d'entrer au moins un mot-clé.")
    else:
        try:
            df = pd.read_csv(sheet_url, header=0)  # on garde header si l'utilisateur a un titre
            raw_col = df.columns[0]
            urls = (
                df[raw_col]
                .dropna()
                .map(str)
                .map(str.strip)
                .loc[lambda x: x != ""]
                .tolist()
            )
        except Exception as e:
            st.error(f"Impossible de lire le Google Sheet : {e}")
            urls = []

        if not urls:
            st.info("Aucune URL valide trouvée dans le Sheet.")
        else:
            st.success(f"{len(urls)} site(s) chargés — démarrage du crawl.")
            st.subheader("URLs trouvées")
            st.table(pd.DataFrame({"URL": urls}))

            # préparation
            keywords = [k.strip() for k in keywords_input.split(",") if k.strip()]
            all_results = []
            prog = st.progress(0)
            status = st.empty()

            total = len(urls)
            for i, seed in enumerate(urls, start=1):
                status.info(f"Crawling {i}/{total} — {seed}")
                with st.spinner(f"Exploration de {seed} …"):
                    site_results = crawl_site(
                        seed_url=seed,
                        keywords=keywords,
                        max_depth=max_depth,
                        max_pages=max_pages,
                        delay=delay,
                        respect_robots=respect_robots
                    )
                all_results.extend(site_results)
                prog.progress(int(i / total * 100))

            status.empty()
            prog.empty()

            if not all_results:
                st.info("Aucun mot-clé trouvé sur les sites et sous-URLs explorés.")
            else:
                st.subheader("Pages contenant des mots-clés")
                df_res = pd.DataFrame(all_results)
                display_cols = ["seed", "url", "title", "matched_keywords"]
                if show_snippet:
                    display_cols.append("snippet")
                st.dataframe(df_res[display_cols].fillna(""), use_container_width=True)

                csv = df_res.to_csv(index=False).encode("utf-8")
                st.download_button("Télécharger les résultats (CSV)", csv, "crawl_results.csv", "text/csv")

            st.success("Crawl terminé.")
