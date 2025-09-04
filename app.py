import streamlit as st
import pandas as pd
import urllib.parse
from ui.sidebar import render_sidebar
from utils.check_for_change import check_for_change
from utils.resouce_table import summarize_content


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
    st.info("Aucune URL valide détectée dans le sheet.")
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

st.success("Vérification terminée pour toutes les URLs.")

# --- Build HTML table ---
st.subheader("Résumé des ressources")

# Table headers
headers = [
    "Liste des entreprises",
    "Type de l'article",
    "Contenu (résumé par IA)",
    "Dernière date de parution",
    "Lien de l'article",
    # "Proposer un article à générer",
    # "Article généré"
]

# Group resources by seed for rowspan effect
# while True, timer 10 minutes
groups = []
for seed in seed_urls:
    resources_for_seed = [r for r in all_resources if r.get("seed") == seed]
    if not resources_for_seed:
        # At least one empty row
        resources_for_seed = [{"title": "", "content": "", "last_date": "", "url": ""}]
    groups.append({
        "label": resources_for_seed[0].get("company_name", seed),  # <- human-readable
        "rows": resources_for_seed
    })


# Build HTML rows
body_rows_html = []
base_url = "http://localhost:8502/"  # generate_app.py URL


for g in groups:
    for i, r in enumerate(g["rows"]):
        first_cell = f'<td rowspan="{len(g["rows"])}">{g["label"]}</td>' if i == 0 else ""
        title = r.get("title", "")
        content = r.get("content", "")
        
        content_summary = summarize_content(content) if content else ""
        # content_snippet = content_summary[:] + "…" if content_summary and len(content_summary) > 200 else content_summary
        content_summary = summarize_content(content) if content else ""
        # Wrap in scrollable div
        content_scrollable = f"""
        <div style="max-height: 12rem; max-width: 40rem; overflow: auto; padding: 4px;">
        {content_summary}
        </div>
        """
        
        last_date = r.get("last_date", "")
        url_link = r.get("url", "")
        article_generated = ""  # Placeholder

        # Build clickable link to generate_app.py
        if url_link:
            query = urllib.parse.urlencode({
                "seed": g["label"],  # human-readable company name
                "title": title,
                "url": url_link
            })
            generate_link = f'<a href="{base_url}?{query}" target="_blank">🔗 Générer</a>'
        else:
            generate_link = ""

        cells = (
            f"<td>{title}</td>"
            f"<td>{content_scrollable}</td>"  # <-- summarized content here
            f"<td>{last_date}</td>"
            f'<td><a href="{url_link}" target="_blank">{url_link}</a></td>'
            # f"<td>{generate_link}</td>"
            # f"<td>{article_generated}</td>"
        )

        body_rows_html.append(f"<tr>{first_cell}{cells}</tr>")

# Combine HTML
body_html = "\n".join(body_rows_html)
header_cells = "".join(f"<th>{h}</th>" for h in headers)


table_html = f"""
<style>
.table-wrap {{ overflow-x: auto; }}
.custom-table {{ 
    border-collapse: collapse; 
    width: 100%; 
    table-layout: fixed;  /* ensures columns respect widths */
    background: white;        
    color: black;             
}}
.custom-table th, .custom-table td {{ 
    border: 1px solid #444; 
    padding: 8px; 
    vertical-align: top; 
    word-wrap: break-word; 
    background: white;        
    color: black;             
}}
.custom-table thead th {{ 
    position: sticky; 
    top: 0; 
    background: #f0f0f0;      
    color: black; 
    z-index: 1; 
}}
.custom-table td:first-child, .custom-table th:first-child {{ 
    font-weight: 600; 
    background: #fafafa;      
    color: black; 
    width: 14rem;  /* company name column */
}}
.custom-table th:nth-child(3), .custom-table td:nth-child(3) {{
    width: 30rem;  /* summary column width */
}}
.custom-table th {{ text-align: left; }}
</style>

<div class="table-wrap">
  <table class="custom-table">
    <thead>
      <tr>{header_cells}</tr>
    </thead>
    <tbody>
      {body_html}
    </tbody>
  </table>
</div>
"""

st.markdown(table_html, unsafe_allow_html=True)
