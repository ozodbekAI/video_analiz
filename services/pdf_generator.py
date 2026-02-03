from weasyprint import HTML, CSS
from datetime import datetime
from pathlib import Path
import re


def clean_html_tags_in_text(text: str) -> str:
    """
    AI javobidagi HTML taglarni tozalash.
    <strong>text</strong> -> text
    """
    if not text:
        return ""
    # HTML taglarni olib tashlash
    text = re.sub(r'</?strong>', '', text)
    text = re.sub(r'</?em>', '', text)
    text = re.sub(r'</?b>', '', text)
    text = re.sub(r'</?i>', '', text)
    text = re.sub(r'</?code>', '', text)
    text = re.sub(r'</?span[^>]*>', '', text)
    return text


def process_inline_formatting(text: str) -> str:
    """Markdown inline formatlash -> HTML"""
    if not text:
        return ""
    # **bold** -> <strong>
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # *italic* -> <em>
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'<em>\1</em>', text)
    # `code` -> <code>
    text = re.sub(r'`([^`]+?)`', r'<code>\1</code>', text)
    return text


def clean_markdown(content: str) -> str:
    """Markdown -> HTML konvertatsiya"""
    
    # AI javobidagi HTML taglarni tozalash
    content = clean_html_tags_in_text(content)
    
    lines = content.split('\n')
    html_parts = []
    in_table = False
    table_lines = []
    in_list = False
    list_items = []
    
    for line in lines:
        stripped = line.strip()
        
        # Jadval boshlanishi/davomi
        if stripped.startswith('|') and stripped.endswith('|'):
            if not in_table:
                # Oldingi listni yopish
                if in_list:
                    html_parts.append(format_list(list_items))
                    list_items = []
                    in_list = False
                in_table = True
                table_lines = []
            table_lines.append(stripped)
            continue
        
        # Jadval tugadi
        if in_table and not stripped.startswith('|'):
            html_parts.append(format_table(table_lines))
            table_lines = []
            in_table = False
        
        # List elementi
        if re.match(r'^[-*]\s+', stripped) or re.match(r'^\d+\.\s+', stripped):
            if not in_list:
                in_list = True
                list_items = []
            # List marker ni olib tashlash
            item_text = re.sub(r'^[-*]\s+', '', stripped)
            item_text = re.sub(r'^\d+\.\s+', '', item_text)
            list_items.append(process_inline_formatting(item_text))
            continue
        
        # List tugadi
        if in_list and stripped and not re.match(r'^[-*]\s+', stripped) and not re.match(r'^\d+\.\s+', stripped):
            html_parts.append(format_list(list_items))
            list_items = []
            in_list = False
        
        # Bo'sh qator
        if not stripped:
            if in_list:
                html_parts.append(format_list(list_items))
                list_items = []
                in_list = False
            continue
        
        # Sarlavhalar
        if stripped.startswith('#'):
            level = 0
            for char in stripped:
                if char == '#':
                    level += 1
                else:
                    break
            if level > 0 and level <= 6:
                text = stripped[level:].strip()
                # Emoji ni ajratish
                emoji_match = re.match(r'^([\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001F600-\U0001F64F\U0001FA00-\U0001FAFF]+)\s*(.+)?$', text)
                if emoji_match:
                    emoji = emoji_match.group(1)
                    title = emoji_match.group(2) or ""
                    html_parts.append(f'<h{level}><span class="emoji">{emoji}</span> {process_inline_formatting(title)}</h{level}>')
                else:
                    html_parts.append(f'<h{level}>{process_inline_formatting(text)}</h{level}>')
                continue
        
        # Oddiy paragraf
        html_parts.append(f'<p>{process_inline_formatting(stripped)}</p>')
    
    # Qolgan jadval/list
    if in_table:
        html_parts.append(format_table(table_lines))
    if in_list:
        html_parts.append(format_list(list_items))
    
    return '\n'.join(html_parts)


def format_list(items: list) -> str:
    """List elementlarini HTML ga aylantirish"""
    if not items:
        return ""
    
    html = '<ul class="styled-list">\n'
    for item in items:
        html += f'  <li>{item}</li>\n'
    html += '</ul>'
    return html


def format_table(table_lines: list) -> str:
    """Jadval qatorlarini HTML ga aylantirish"""
    if len(table_lines) < 2:
        return ""
    
    # Birinchi qator - sarlavhalar
    headers = [cell.strip() for cell in table_lines[0].strip('|').split('|')]
    
    # Ikkinchi qator separator (---) bo'lishi mumkin
    rows = []
    for i, line in enumerate(table_lines[1:]):
        cells = [cell.strip() for cell in line.strip('|').split('|')]
        # Separator qatorni o'tkazish
        if all(re.match(r'^[-:]+$', cell) for cell in cells):
            continue
        rows.append(cells)
    
    if not rows:
        return ""
    
    col_count = len(headers)
    
    # Ustun kengliklarini hisoblash
    max_lens = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(max_lens):
                max_lens[i] = max(max_lens[i], len(str(cell)))
    
    total = sum(max_lens) or 1
    widths = [f"{(l/total)*100:.1f}%" for l in max_lens]
    
    # Jadval klassi
    if col_count >= 8:
        table_class = "table-tiny"
    elif col_count >= 6:
        table_class = "table-small"
    elif col_count >= 4:
        table_class = "table-medium"
    else:
        table_class = "table-large"
    
    html = f'<div class="table-container"><table class="{table_class}">\n'
    
    # Colgroup
    html += '<colgroup>\n'
    for w in widths:
        html += f'  <col style="width: {w};">\n'
    html += '</colgroup>\n'
    
    # Header
    html += '<thead><tr>\n'
    for h in headers:
        clean_header = clean_html_tags_in_text(h)
        html += f'  <th>{process_inline_formatting(clean_header)}</th>\n'
    html += '</tr></thead>\n'
    
    # Body
    html += '<tbody>\n'
    for row in rows:
        html += '<tr>\n'
        for i, cell in enumerate(row):
            clean_cell = clean_html_tags_in_text(str(cell)) if cell else '—'
            formatted = process_inline_formatting(clean_cell)
            if not formatted.strip():
                formatted = '—'
            html += f'  <td>{formatted}</td>\n'
        # Kam ustunli qatorlarni to'ldirish
        for _ in range(col_count - len(row)):
            html += '  <td>—</td>\n'
        html += '</tr>\n'
    html += '</tbody>\n'
    
    html += '</table></div>\n'
    return html


def generate_pdf(content: str, video_url: str, video_id: str) -> str:
    """PDF hisobot yaratish"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_path = f"report_{video_id}_{timestamp}.pdf"
    
    html_content = clean_markdown(content)
    
    html_template = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <title>Анализ комментариев - {video_id}</title>
</head>
<body>
    <header class="report-header">
        <div class="logo">📊</div>
        <h1 class="main-title">СТРАТЕГИЧЕСКИЙ АНАЛИЗ</h1>
        <div class="subtitle">Аналитический отчет по комментариям</div>
    </header>
    
    <div class="meta-box">
        <div class="meta-row">
            <span class="meta-label">🎬 Видео:</span>
            <a href="{video_url}" class="meta-link">{video_url}</a>
        </div>
        <div class="meta-row">
            <span class="meta-label">📅 Дата:</span>
            <span>{datetime.now().strftime('%d.%m.%Y в %H:%M')}</span>
        </div>
        <div class="meta-row">
            <span class="meta-label">🆔 ID:</span>
            <span class="video-id">{video_id}</span>
        </div>
    </div>
    
    <main class="content">
        {html_content}
    </main>
    
    <footer class="report-footer">
        <div class="footer-line"></div>
        <p>Автоматически сгенерированный отчет • Video Analyzer Bot</p>
    </footer>
</body>
</html>"""
    
    css_styles = """
/* ═══════════════════════════════════════════════════════════════
   PROFESSIONAL PDF STYLES - Video Analyzer Report
   ═══════════════════════════════════════════════════════════════ */

@page {
    size: A4;
    margin: 2cm 1.5cm 2cm 1.5cm;
    
    @bottom-center {
        content: "Страница " counter(page) " из " counter(pages);
        font-size: 8pt;
        color: #6b7280;
        font-family: 'DejaVu Sans', Arial, sans-serif;
    }
}

/* ─────────────────────────────────────────────────────────────────
   BASE STYLES
   ───────────────────────────────────────────────────────────────── */

body {
    font-family: 'DejaVu Sans', 'Noto Sans', Arial, sans-serif;
    font-size: 10pt;
    line-height: 1.6;
    color: #1f2937;
    background: #ffffff;
    margin: 0;
    padding: 0;
}

/* ─────────────────────────────────────────────────────────────────
   HEADER
   ───────────────────────────────────────────────────────────────── */

.report-header {
    text-align: center;
    padding: 25px 20px;
    margin-bottom: 20px;
    border-bottom: 3px solid #2563eb;
    background: #f0f9ff;
    border-radius: 8px 8px 0 0;
}

.report-header .logo {
    font-size: 40pt;
    margin-bottom: 10px;
}

.report-header .main-title {
    font-size: 22pt;
    color: #1e40af;
    margin: 0;
    font-weight: 700;
    letter-spacing: 2px;
    border: none;
    padding: 0;
}

.report-header .subtitle {
    font-size: 11pt;
    color: #6b7280;
    margin-top: 8px;
}

/* ─────────────────────────────────────────────────────────────────
   META BOX
   ───────────────────────────────────────────────────────────────── */

.meta-box {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 15px 20px;
    margin-bottom: 25px;
}

.meta-row {
    margin: 8px 0;
    font-size: 9pt;
}

.meta-label {
    font-weight: 600;
    color: #475569;
    margin-right: 10px;
}

.meta-link {
    color: #2563eb;
    text-decoration: none;
    word-break: break-all;
}

.video-id {
    font-family: monospace;
    background: #e2e8f0;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 8pt;
}

/* ─────────────────────────────────────────────────────────────────
   HEADINGS
   ───────────────────────────────────────────────────────────────── */

h1, h2, h3, h4, h5, h6 {
    page-break-after: avoid;
    margin-top: 24px;
    margin-bottom: 12px;
}

h1 {
    font-size: 15pt;
    color: #1e40af;
    border-bottom: 2px solid #3b82f6;
    padding-bottom: 8px;
    margin-top: 30px;
}

h1 .emoji {
    font-size: 16pt;
    margin-right: 8px;
}

h2 {
    font-size: 12pt;
    color: #dc2626;
    border-left: 4px solid #dc2626;
    padding: 8px 12px;
    background: #fef2f2;
    border-radius: 0 6px 6px 0;
    margin-top: 20px;
}

h3 {
    font-size: 11pt;
    color: #059669;
    border-left: 3px solid #10b981;
    padding-left: 10px;
}

h4 {
    font-size: 10pt;
    color: #7c3aed;
    font-weight: 600;
}

h5, h6 {
    font-size: 9pt;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ─────────────────────────────────────────────────────────────────
   PARAGRAPHS & TEXT
   ───────────────────────────────────────────────────────────────── */

p {
    margin: 8px 0;
    text-align: justify;
    orphans: 3;
    widows: 3;
}

strong {
    color: #b91c1c;
    font-weight: 700;
}

em {
    color: #0d9488;
    font-style: italic;
}

code {
    font-family: 'DejaVu Sans Mono', monospace;
    background: #f1f5f9;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 9pt;
    color: #7c3aed;
}

/* ─────────────────────────────────────────────────────────────────
   LISTS
   ───────────────────────────────────────────────────────────────── */

.styled-list {
    margin: 12px 0;
    padding-left: 0;
    list-style: none;
}

.styled-list li {
    position: relative;
    padding: 6px 0 6px 24px;
    margin: 4px 0;
    border-left: 2px solid #e2e8f0;
}

.styled-list li::before {
    content: "▸";
    position: absolute;
    left: 8px;
    color: #3b82f6;
    font-weight: bold;
}

/* ─────────────────────────────────────────────────────────────────
   TABLES - RESPONSIVE
   ───────────────────────────────────────────────────────────────── */

.table-container {
    margin: 16px 0;
    page-break-inside: avoid;
}

table {
    width: 100%;
    border-collapse: collapse;
    border: 1px solid #cbd5e1;
    border-radius: 6px;
    overflow: hidden;
    table-layout: fixed;
    word-wrap: break-word;
}

/* Table sizes */
.table-large { font-size: 9pt; }
.table-large th, .table-large td { padding: 10px 8px; }

.table-medium { font-size: 8pt; }
.table-medium th, .table-medium td { padding: 8px 6px; }

.table-small { font-size: 7pt; }
.table-small th, .table-small td { padding: 6px 4px; }

.table-tiny { font-size: 6pt; }
.table-tiny th, .table-tiny td { padding: 4px 3px; line-height: 1.2; }

/* Header */
thead {
    display: table-header-group;
}

th {
    background: #3b82f6;
    color: #ffffff;
    font-weight: 600;
    text-align: left;
    border-bottom: 2px solid #1e40af;
    word-wrap: break-word;
    overflow-wrap: break-word;
    hyphens: auto;
}

/* Cells */
td {
    border: 1px solid #e2e8f0;
    vertical-align: top;
    word-wrap: break-word;
    overflow-wrap: break-word;
    hyphens: auto;
}

/* Zebra striping */
tbody tr:nth-child(even) {
    background: #f8fafc;
}

tbody tr:nth-child(odd) {
    background: #ffffff;
}

/* First column highlight */
td:first-child {
    font-weight: 500;
    color: #1e40af;
    background: #f0f9ff;
}

/* ─────────────────────────────────────────────────────────────────
   FOOTER
   ───────────────────────────────────────────────────────────────── */

.report-footer {
    margin-top: 40px;
    text-align: center;
}

.footer-line {
    height: 2px;
    background: linear-gradient(90deg, transparent, #cbd5e1, transparent);
    margin-bottom: 15px;
}

.report-footer p {
    font-size: 8pt;
    color: #9ca3af;
    margin: 0;
}

/* ─────────────────────────────────────────────────────────────────
   PRINT OPTIMIZATIONS
   ───────────────────────────────────────────────────────────────── */

@media print {
    .table-container {
        page-break-inside: avoid;
    }
    
    tr {
        page-break-inside: avoid;
        page-break-after: auto;
    }
    
    thead {
        display: table-header-group;
    }
    
    h1, h2, h3, h4 {
        page-break-after: avoid;
    }
    
    p {
        orphans: 3;
        widows: 3;
    }
}
"""
    
    HTML(string=html_template).write_pdf(
        output_path,
        stylesheets=[CSS(string=css_styles)]
    )
    
    return output_path
