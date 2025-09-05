def build_html_table(headers, body_html, blink=False):
    header_cells = "".join(f"<th>{h}</th>" for h in headers)

    css_base = """
    .table-wrap { overflow-x: auto; }
    .custom-table { 
        border-collapse: collapse; 
        width: 100%; 
        table-layout: fixed;  
        background: white;        
        color: black;             
    }
    .custom-table th, .custom-table td { 
        border: 1px solid #444; 
        padding: 8px; 
        vertical-align: top; 
        word-wrap: break-word; 
        background: white;        
        color: black;             
    }
    .custom-table thead th { 
        position: sticky; 
        top: 0; 
        background: #f0f0f0;      
        color: black; 
        z-index: 1; 
    }
    .custom-table td:first-child, .custom-table th:first-child { 
        font-weight: 600; 
        background: #fafafa;      
        color: black; 
        width: 14rem;  
    }
    .custom-table th:nth-child(3), .custom-table td:nth-child(3) {
        width: 30rem;  
    }
    .custom-table th { text-align: left; }
    """

    css_blink = """
    @keyframes blink-border {
      0%   { border: 2px solid red; }
      50%  { border: 2px solid transparent; }
      100% { border: 2px solid red; }
    }
    .blink-border td {
      animation: blink-border 1.5s infinite;
    }
    """ if blink else ""

    return f"""
    <style>
    {css_blink}
    {css_base}
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


def build_body_rows(groups, summarize_content, blink=False):
    base_url = "http://localhost:8502/"
    body_rows_html = []

    for g in groups:
        for i, r in enumerate(g["rows"]):
            first_cell = f'<td rowspan="{len(g["rows"])}">{g["label"]}</td>' if i == 0 else ""
            title = r.get("title", "")
            content = r.get("content", "")
            content_summary = summarize_content(content) if content else ""
            content_scrollable = f"""
            <div style="max-height: 12rem; max-width: 40rem; overflow: auto; padding: 4px;">
            {content_summary}
            </div>
            """
            last_date = r.get("last_date", "")
            url_link = r.get("url", "")

            cells = (
                f"<td>{title}</td>"
                f"<td>{content_scrollable}</td>"
                f"<td>{last_date}</td>"
                f'<td><a href="{url_link}" target="_blank">{url_link}</a></td>'
            )

            tr_class = " class='blink-border'" if blink else ""
            body_rows_html.append(f"<tr{tr_class}>{first_cell}{cells}</tr>")

    return "\n".join(body_rows_html)
