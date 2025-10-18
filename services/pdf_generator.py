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
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('|') and '|' in stripped[1:]:
            if not in_table:
                formatted_lines.append('<table>')
                in_table = True
            
            cells = [cell.strip() for cell in stripped.strip('|').split('|')]
            formatted_lines.append('<tr>')
            
            if all('---' in cell or cell == '' for cell in cells):
                continue
                
            if len(formatted_lines) == 2:  
                for cell in cells:
                    formatted_lines.append(f'<th>{cell}</th>')
            else:
                for cell in cells:
                    formatted_lines.append(f'<td>{cell}</td>')
            
            formatted_lines.append('</tr>')
        else:
            if in_table:
                formatted_lines.append('</table>')
                in_table = False
            
            
            if stripped and not stripped.startswith('<h'):
                formatted_lines.append(f'<p>{stripped}</p>')
            elif stripped.startswith('<h'):
                formatted_lines.append(stripped)
    
    if in_table:
        formatted_lines.append('</table>')
    
    return '\n'.join(formatted_lines)


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
                <p><strong>Дата анализа:</strong> {datetime.now().strftime('%d.%m.%Y %H:%M')}</p>
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
    
    
    css_style = """
    @page {
        size: A4;
        margin: 2cm 1.5cm;
        @bottom-center {
            content: counter(page) " / " counter(pages);
            font-size: 9pt;
            color: #666;
        }
    }
    
    body {
        font-family: 'DejaVu Sans', Arial, sans-serif;
        font-size: 11pt;
        line-height: 1.6;
        color: #2c3e50;
        background: #ffffff;
    }
    
    .header {
        text-align: center;
        border-bottom: 3px solid #3498db;
        padding-bottom: 20px;
        margin-bottom: 30px;
    }
    
    .header h1 {
        color: #2c3e50;
        font-size: 24pt;
        margin-bottom: 15px;
        font-weight: bold;
    }
    
    .meta {
        background: #ecf0f1;
        padding: 15px;
        border-radius: 8px;
        text-align: left;
        display: inline-block;
        margin: 0 auto;
    }
    
    .meta p {
        margin: 5px 0;
        font-size: 10pt;
    }
    
    .meta a {
        color: #3498db;
        text-decoration: none;
    }
    
    .content {
        margin-top: 20px;
    }
    
    h1 {
        color: #2980b9;
        font-size: 18pt;
        margin-top: 25px;
        margin-bottom: 12px;
        border-left: 4px solid #3498db;
        padding-left: 12px;
    }
    
    h2 {
        color: #e74c3c;
        font-size: 15pt;
        margin-top: 20px;
        margin-bottom: 10px;
        border-left: 3px solid #e74c3c;
        padding-left: 10px;
    }
    
    h3 {
        color: #27ae60;
        font-size: 13pt;
        margin-top: 15px;
        margin-bottom: 8px;
    }
    
    h4 {
        color: #8e44ad;
        font-size: 11pt;
        margin-top: 12px;
        margin-bottom: 6px;
    }
    
    p {
        margin: 8px 0;
        text-align: justify;
    }
    
    strong {
        color: #c0392b;
        font-weight: bold;
    }
    
    em {
        color: #16a085;
        font-style: italic;
    }
    
    table {
        width: 100%;
        border-collapse: collapse;
        margin: 20px 0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    th {
        background: #3498db;
        color: white;
        padding: 12px;
        text-align: left;
        font-weight: bold;
        font-size: 10pt;
    }
    
    td {
        padding: 10px 12px;
        border: 1px solid #ddd;
        font-size: 10pt;
    }
    
    tr:nth-child(even) {
        background: #f8f9fa;
    }
    
    tr:hover {
        background: #e8f4f8;
    }
    
    .footer {
        margin-top: 40px;
        padding-top: 20px;
        border-top: 2px solid #bdc3c7;
        text-align: center;
        font-size: 9pt;
        color: #7f8c8d;
    }
    """
    
    HTML(string=html_template).write_pdf(
        temp_path,
        stylesheets=[CSS(string=css_style)]
    )
    
    print(f"✅ PDF сгенерирован: {temp_path}")
    return temp_path