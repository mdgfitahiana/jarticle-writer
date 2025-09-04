import streamlit as st

st.set_page_config(page_title="Tableau Entreprises & Articles", layout="wide")
st.title("Tableau : Entreprises et Articles")

# 1) Titres des colonnes
headers = [
    "Liste des entreprises",
    "Type de l'article",
    "Contenu (résumé par IA)",
    "Dernière date de parution",
    "Lien de l'article",
    "Proposer un article à générer",
    "Article généré"
]

# 2) Lignes principales (colonne 1)
entreprises = ["Accor", "TotalEnergies", "LVMH", "Etc", "Etc"]

# 3) Générer les 5 groupes (chaque entreprise avec 4 sous-lignes)
def blank_subrows(n_cols=6):
    # 4 sous-lignes vides pour les colonnes 2→7
    return [["" for _ in range(n_cols)] for __ in range(4)]

groups = [{"label": e, "rows": blank_subrows()} for e in entreprises]

# 4) Construire le tableau
header_cells = "".join(f"<th>{h}</th>" for h in headers)

body_rows_html = []
for g in groups:
    for i, sub in enumerate(g["rows"]):
        # 1ere sous-ligne → insérer le nom de l’entreprise avec rowspan=4
        first_cell = f'<td rowspan="4">{g["label"]}</td>' if i == 0 else ""
        cells = "".join(f"<td>{c}</td>" for c in sub)
        body_rows_html.append(f"<tr>{first_cell}{cells}</tr>")

body_html = "\n".join(body_rows_html)

table_html = f"""
<style>
.table-wrap {{ overflow-x: auto; }}
.custom-table {{ 
    border-collapse: collapse; 
    width: 100%; 
    table-layout: fixed; 
    background: white;        /* Forcer fond blanc */
    color: black;             /* Forcer texte noir */
}}
.custom-table th, .custom-table td {{ 
    border: 1px solid #444; 
    padding: 8px; 
    vertical-align: top; 
    word-wrap: break-word; 
    background: white;        /* Fond blanc pour toutes cellules */
    color: black;             /* Texte noir */
}}
.custom-table thead th {{ 
    position: sticky; 
    top: 0; 
    background: #f0f0f0;      /* En-têtes gris clair */
    color: black; 
    z-index: 1; 
}}
.custom-table td:first-child, .custom-table th:first-child {{ 
    font-weight: 600; 
    background: #fafafa;      /* Colonne entreprises en gris clair */
    color: black; 
    width: 14rem; 
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


