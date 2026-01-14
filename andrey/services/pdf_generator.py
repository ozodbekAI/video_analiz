from weasyprint import HTML, CSS
from datetime import datetime
from pathlib import Path
import re


def clean_markdown(text: str) -> str:

    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)
    
    text = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h2>\1</h2>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$', r'<h1>\1</h1>', text, flags=re.MULTILINE)
    
    lines = text.split('\n')
    formatted_lines = []
    in_table = False
    table_headers = []
    table_rows = []
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('|') and '|' in stripped[1:]:
            if not in_table:
                in_table = True
                table_headers = []
                table_rows = []
            
            if all(cell.strip() == '' or re.match(r'^-+$', cell.strip()) for cell in stripped.strip('|').split('|')):
                continue

            cells = [cell.strip() for cell in stripped.strip('|').split('|')]
            
            if not table_headers:
                table_headers = cells
            else:
                table_rows.append(cells)
        

        else:
            if in_table:
                formatted_lines.append(format_responsive_table(table_headers, table_rows))
                in_table = False
                table_headers = []
                table_rows = []
            
            if stripped and not stripped.startswith('<h'):
                formatted_lines.append(f'<p>{stripped}</p>')
            elif stripped.startswith('<h'):
                formatted_lines.append(stripped)
    
    if in_table:
        formatted_lines.append(format_responsive_table(table_headers, table_rows))
    
    return '\n'.join(formatted_lines)


def format_responsive_table(headers: list, rows: list) -> str:
    if not headers or not rows:
        return ""
    
    col_count = len(headers)
    
    # USTUNLAR KENGLIGI HISOBLASH
    max_lengths = [len(str(h)) for h in headers]
    
    for row in rows:
        for idx, cell in enumerate(row):
            if idx < len(max_lengths):
                max_lengths[idx] = max(max_lengths[idx], len(str(cell)))
    
    total_length = sum(max_lengths)
    
    col_widths = []
    for length in max_lengths:
        width_percent = (length / total_length * 100) if total_length > 0 else (100 / col_count)
        col_widths.append(f"{width_percent:.1f}%")
    
    if col_count >= 5:
        table_class = "table-small" 
    elif col_count >= 3:
        table_class = "table-medium" 
    else:
        table_class = "table-large" 
    

    html = f'<div class="table-wrapper"><table class="{table_class}">\n'
    
    html += '<colgroup>\n'
    for width in col_widths:
        html += f'<col style="width: {width};">\n'
    html += '</colgroup>\n'

    html += '<thead><tr>\n'
    for header in headers:
        html += f'<th>{escape_html(str(header))}</th>\n'
    html += '</tr></thead>\n'
    
    html += '<tbody>\n'
    for row in rows:
        html += '<tr>\n'
        for cell in row:
            cell_content = escape_html(str(cell)) if cell else '—'
            html += f'<td>{cell_content}</td>\n'
        html += '</tr>\n'
    html += '</tbody>\n'
    
    html += '</table></div>\n'
    
    return html


def escape_html(text: str) -> str:
    return (text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
        )


def generate_pdf(content: str, video_url: str, video_id: str) -> str:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    temp_path = f"report_{video_id}_{timestamp}.pdf"
    
    html_content = clean_markdown(content)
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>Анализ комментариев</title>
    </head>
    <body>
        <div class="header">
            <h1>📊 АНАЛИЗ КОММЕНТАРИЕВ</h1>
            <div class="meta">
                <p><strong>Видео:</strong> <a href="{video_url}">{video_url}</a></p>
                <p><strong>Дата:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
            </div>
        </div>
        
        <div class="content">
            {html_content}
        </div>
        
        <div class="footer">
            <p>Сгенерировано автоматически | Video ID: {video_id}</p>
        </div>
    </body>
    </html>
    """
    
    # ✅ OPTIMIZATSIYALANGAN CSS
    css_style = """
    @page {
        size: A4;
        margin: 1.5cm 1cm;
        @bottom-center {
            content: counter(page) " / " counter(pages);
            font-size: 8pt;
            color: #666;
        }
    }
    
    body {
        font-family: 'DejaVu Sans', Arial, sans-serif;
        font-size: 10pt;
        line-height: 1.5;
        color: #2c3e50;
        background: #ffffff;
    }
    
    /* HEADER */
    .header {
        text-align: center;
        border-bottom: 3px solid #3498db;
        padding-bottom: 15px;
        margin-bottom: 25px;
    }
    
    .header h1 {
        color: #2c3e50;
        font-size: 22pt;
        margin-bottom: 12px;
        font-weight: bold;
    }
    
    .meta {
        background: #ecf0f1;
        padding: 12px;
        border-radius: 6px;
        text-align: left;
        display: inline-block;
        margin: 0 auto;
    }
    
    .meta p {
        margin: 4px 0;
        font-size: 9pt;
    }
    
    .meta a {
        color: #3498db;
        text-decoration: none;
        word-break: break-all;
    }
    
    /* CONTENT */
    .content {
        margin-top: 15px;
    }
    
    h1 {
        color: #2980b9;
        font-size: 16pt;
        margin-top: 20px;
        margin-bottom: 10px;
        border-left: 4px solid #3498db;
        padding-left: 10px;
        page-break-after: avoid;
    }
    
    h2 {
        color: #e74c3c;
        font-size: 14pt;
        margin-top: 16px;
        margin-bottom: 8px;
        border-left: 3px solid #e74c3c;
        padding-left: 8px;
        page-break-after: avoid;
    }
    
    h3 {
        color: #27ae60;
        font-size: 12pt;
        margin-top: 12px;
        margin-bottom: 6px;
        page-break-after: avoid;
    }
    
    h4 {
        color: #8e44ad;
        font-size: 10pt;
        margin-top: 10px;
        margin-bottom: 5px;
        page-break-after: avoid;
    }
    
    p {
        margin: 6px 0;
        text-align: justify;
        orphans: 2;
        widows: 2;
    }
    
    strong {
        color: #c0392b;
        font-weight: bold;
    }
    
    em {
        color: #16a085;
        font-style: italic;
    }
    
    /* ✅ RESPONSIVE TABLES */
    .table-wrapper {
        margin: 15px 0;
        overflow: visible;
        page-break-inside: avoid;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        table-layout: fixed;
        word-wrap: break-word;
    }
    
    /* ✅ KATTA JADVAL (1-2 ustun) */
    .table-large {
        font-size: 9pt;
    }
    
    .table-large th,
    .table-large td {
        padding: 8px 6px;
        font-size: 9pt;
    }
    
    /* ✅ O'RTACHA JADVAL (3-4 ustun) */
    .table-medium {
        font-size: 8pt;
    }
    
    .table-medium th,
    .table-medium td {
        padding: 6px 4px;
        font-size: 8pt;
    }
    
    /* ✅ KICHIK JADVAL (5+ ustun) */
    .table-small {
        font-size: 7pt;
    }
    
    .table-small th,
    .table-small td {
        padding: 4px 2px;
        font-size: 7pt;
        line-height: 1.3;
    }
    
    /* ✅ UMUMIY JADVAL STILLARI */
    th {
        background: #3498db;
        color: white;
        text-align: left;
        font-weight: bold;
        word-wrap: break-word;
        overflow-wrap: break-word;
        hyphens: auto;
    }
    
    td {
        border: 1px solid #ddd;
        word-wrap: break-word;
        overflow-wrap: break-word;
        hyphens: auto;
        vertical-align: top;
    }
    
    /* Bo'sh katakchalar */
    td:empty::before {
        content: "—";
        color: #bdc3c7;
    }
    
    /* Zebra striping */
    tbody tr:nth-child(even) {
        background: #f8f9fa;
    }
    
    tbody tr:hover {
        background: #e8f4f8;
    }
    
    /* FOOTER */
    .footer {
        margin-top: 30px;
        padding-top: 15px;
        border-top: 2px solid #bdc3c7;
        text-align: center;
        font-size: 8pt;
        color: #7f8c8d;
    }
    
    /* ✅ PRINT OPTIMIZATIONS */
    @media print {
        table {
            page-break-inside: avoid;
        }
        
        tr {
            page-break-inside: avoid;
            page-break-after: auto;
        }
        
        thead {
            display: table-header-group;
        }
        
        tfoot {
            display: table-footer-group;
        }
    }
    """
    
    HTML(string=html_template).write_pdf(
        temp_path,
        stylesheets=[CSS(string=css_style)]
    )
    
    return temp_path