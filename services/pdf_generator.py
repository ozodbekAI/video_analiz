from weasyprint import HTML, CSS
from datetime import datetime
from pathlib import Path
import re
import json


def format_evaluation_json_to_table(json_data: dict | str) -> str:
    """
    Multi-analysis evaluator JSON ni rus tilida chiroyli jadval formatiga aylantirish.
    Oddiy foydalanuvchi uchun tushunarli ko'rinish.
    """
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except:
            return ""
    
    if not json_data or not isinstance(json_data, dict):
        return ""
    
    html_parts = []
    
    # Sarlavha
    html_parts.append('<div class="evaluation-section">')
    html_parts.append('<h2>📊 СРАВНИТЕЛЬНАЯ ОЦЕНКА АНАЛИЗОВ</h2>')
    
    # Eng yaxshi analiz
    best_id = json_data.get("best_analysis_id", "—")
    selection_reason = json_data.get("selection_reason", "")
    
    html_parts.append(f'''
    <div class="best-analysis-box">
        <div class="best-label">🏆 ЛУЧШИЙ АНАЛИЗ</div>
        <div class="best-id">Анализ #{best_id}</div>
        <div class="best-reason">{selection_reason}</div>
    </div>
    ''')
    
    # Evaluations jadvali
    evaluations = json_data.get("evaluations", [])
    if evaluations:
        html_parts.append('<h3>📋 Детальные оценки</h3>')
        html_parts.append('<table class="evaluation-table">')
        html_parts.append('''
        <thead>
            <tr>
                <th>Анализ</th>
                <th>Полнота</th>
                <th>Структура</th>
                <th>Глубина</th>
                <th>Ценность</th>
                <th>Ясность</th>
                <th>ИТОГО</th>
                <th>Ранг</th>
            </tr>
        </thead>
        <tbody>
        ''')
        
        for ev in evaluations:
            analysis_id = ev.get("analysis_id", "—")
            scores = ev.get("scores", {})
            total = ev.get("total_score", 0)
            rank = ev.get("quality_rank", "—")
            
            # Rang uchun klass
            rank_class = "rank-1" if rank == 1 else ("rank-2" if rank == 2 else "rank-other")
            
            html_parts.append(f'''
            <tr class="{rank_class}">
                <td><strong>#{analysis_id}</strong></td>
                <td>{scores.get("completeness", "—")}</td>
                <td>{scores.get("structure", "—")}</td>
                <td>{scores.get("insights_depth", "—")}</td>
                <td>{scores.get("practical_value", "—")}</td>
                <td>{scores.get("clarity", "—")}</td>
                <td class="total-score"><strong>{total:.1f}</strong></td>
                <td class="rank">#{rank}</td>
            </tr>
            ''')
        
        html_parts.append('</tbody></table>')
        
        # Kuchli va zaif tomonlar
        for ev in evaluations:
            analysis_id = ev.get("analysis_id", "—")
            strengths = ev.get("strengths", [])
            weaknesses = ev.get("weaknesses", [])
            suggestions = ev.get("improvement_suggestions", [])
            
            if strengths or weaknesses or suggestions:
                html_parts.append(f'<div class="analysis-details">')
                html_parts.append(f'<h4>Анализ #{analysis_id}</h4>')
                
                if strengths:
                    html_parts.append('<div class="strengths"><strong>✅ Сильные стороны:</strong><ul>')
                    for s in strengths[:3]:
                        html_parts.append(f'<li>{s}</li>')
                    html_parts.append('</ul></div>')
                
                if weaknesses:
                    html_parts.append('<div class="weaknesses"><strong>⚠️ Слабые стороны:</strong><ul>')
                    for w in weaknesses[:3]:
                        html_parts.append(f'<li>{w}</li>')
                    html_parts.append('</ul></div>')
                
                if suggestions:
                    html_parts.append('<div class="suggestions"><strong>💡 Рекомендации:</strong><ul>')
                    for s in suggestions[:2]:
                        html_parts.append(f'<li>{s}</li>')
                    html_parts.append('</ul></div>')
                
                html_parts.append('</div>')
    
    # Umumiy xulosalar
    comparison = json_data.get("comparison_summary", "")
    overall_recs = json_data.get("overall_recommendations", [])
    
    if comparison:
        html_parts.append(f'''
        <div class="comparison-summary">
            <h4>📝 Общее сравнение</h4>
            <p>{comparison}</p>
        </div>
        ''')
    
    if overall_recs:
        html_parts.append('<div class="overall-recommendations">')
        html_parts.append('<h4>🎯 Общие рекомендации</h4><ul>')
        for rec in overall_recs[:5]:
            html_parts.append(f'<li>{rec}</li>')
        html_parts.append('</ul></div>')
    
    html_parts.append('</div>')  # evaluation-section
    
    return '\n'.join(html_parts)


def format_machine_data_to_table(json_data: dict | str) -> str:
    """
    Machine data JSON ni rus tilida chiroyli jadval formatiga aylantirish.
    ДАННЫЕ ДЛЯ АГРЕГАЦИИ -> Odam uchun tushunarli jadval.
    """
    if isinstance(json_data, str):
        try:
            json_data = json.loads(json_data)
        except:
            return ""
    
    if not json_data or not isinstance(json_data, dict):
        return ""
    
    html_parts = []
    html_parts.append('<div class="machine-data-section">')
    html_parts.append('<h2>📊 КЛЮЧЕВЫЕ МЕТРИКИ АНАЛИЗА</h2>')
    
    # Video metadata
    video_meta = json_data.get("video_metadata", {})
    if video_meta:
        html_parts.append('''
        <table class="metrics-table">
        <thead><tr><th colspan="2">🎬 Информация о видео</th></tr></thead>
        <tbody>
        ''')
        
        labels = {
            "video_id": "ID видео",
            "title": "Название",
            "upload_date": "Дата загрузки",
            "comments_count": "Количество комментариев",
            "analysis_period": "Период анализа"
        }
        
        for key, label in labels.items():
            value = video_meta.get(key, "—")
            html_parts.append(f'<tr><td><strong>{label}</strong></td><td>{value}</td></tr>')
        
        html_parts.append('</tbody></table>')
    
    # Content metrics
    content_metrics = json_data.get("content_metrics", {})
    if content_metrics:
        html_parts.append('''
        <table class="metrics-table">
        <thead><tr><th colspan="2">📈 Метрики контента</th></tr></thead>
        <tbody>
        ''')
        
        labels = {
            "analytically_valuable_comments_percentage": "Ценные комментарии (%)",
            "theme_diversity_index": "Индекс разнообразия тем",
            "top_theme_id": "Топ тема",
            "top_theme_score": "Оценка топ темы"
        }
        
        for key, label in labels.items():
            value = content_metrics.get(key, "—")
            if isinstance(value, float):
                value = f"{value:.1f}"
            html_parts.append(f'<tr><td><strong>{label}</strong></td><td>{value}</td></tr>')
        
        html_parts.append('</tbody></table>')
    
    # Emotional metrics
    emotional_metrics = json_data.get("emotional_metrics", {})
    if emotional_metrics:
        html_parts.append('''
        <table class="metrics-table">
        <thead><tr><th colspan="2">😊 Эмоциональные метрики</th></tr></thead>
        <tbody>
        ''')
        
        labels = {
            "emotional_saturation_index": "Индекс эмоц. насыщенности",
            "emotional_diversity_coefficient": "Коэфф. разнообразия эмоций",
            "predominant_emotion": "Преобладающая эмоция",
            "predominant_emotion_percentage": "Доля эмоции (%)",
            "emotional_weather": "Эмоциональная погода"
        }
        
        for key, label in labels.items():
            value = emotional_metrics.get(key, "—")
            if isinstance(value, float):
                value = f"{value:.1f}"
            html_parts.append(f'<tr><td><strong>{label}</strong></td><td>{value}</td></tr>')
        
        html_parts.append('</tbody></table>')
    
    # Strategic indices
    strategic = json_data.get("strategic_indices", {})
    if strategic:
        html_parts.append('''
        <table class="metrics-table">
        <thead><tr><th colspan="2">🎯 Стратегические индексы</th></tr></thead>
        <tbody>
        ''')
        
        labels = {
            "content_health_index": "Индекс здоровья контента",
            "audience_evolution_vector": "Вектор развития аудитории",
            "strategic_stability_index": "Индекс стратег. стабильности",
            "data_quality": "Качество данных"
        }
        
        for key, label in labels.items():
            value = strategic.get(key, "—")
            html_parts.append(f'<tr><td><strong>{label}</strong></td><td>{value}</td></tr>')
        
        html_parts.append('</tbody></table>')
    
    # Key insights
    insights = json_data.get("key_insights_summary", [])
    if insights:
        html_parts.append('<div class="key-insights">')
        html_parts.append('<h3>💡 Ключевые инсайты</h3><ul>')
        for insight in insights:
            html_parts.append(f'<li>{insight}</li>')
        html_parts.append('</ul></div>')
    
    html_parts.append('</div>')  # machine-data-section
    
    return '\n'.join(html_parts)


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
    in_code_block = False
    code_block_lines = []
    code_block_lang = ""
    
    for line in lines:
        stripped = line.strip()
        
        # Code block (```json, ```python, etc.)
        if stripped.startswith('```'):
            if not in_code_block:
                # Code block boshlanishi
                in_code_block = True
                code_block_lang = stripped[3:].strip().lower()
                code_block_lines = []
                # Oldingi list/table yopish
                if in_list:
                    html_parts.append(format_list(list_items))
                    list_items = []
                    in_list = False
                if in_table:
                    html_parts.append(format_table(table_lines))
                    table_lines = []
                    in_table = False
            else:
                # Code block tugashi
                in_code_block = False
                html_parts.append(format_code_block(code_block_lines, code_block_lang))
                code_block_lines = []
                code_block_lang = ""
            continue
        
        # Code block ichida
        if in_code_block:
            code_block_lines.append(line)  # Original indentation saqlanadi
            continue
        
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
                
                # Maxsus markerlar uchun stil
                if 'ДАННЫЕ ДЛЯ АГРЕГАЦИИ' in text or 'METRICS' in text.upper():
                    html_parts.append(f'<div class="metrics-header">{text}</div>')
                    continue
                
                # Emoji ni ajratish
                emoji_match = re.match(r'^([\U0001F300-\U0001F9FF\U00002600-\U000027BF\U0001F600-\U0001F64F\U0001FA00-\U0001FAFF]+)\s*(.+)?$', text)
                if emoji_match:
                    emoji = emoji_match.group(1)
                    title = emoji_match.group(2) or ""
                    html_parts.append(f'<h{level}><span class="emoji">{emoji}</span> {process_inline_formatting(title)}</h{level}>')
                else:
                    html_parts.append(f'<h{level}>{process_inline_formatting(text)}</h{level}>')
                continue
        
        # Maxsus end marker
        if 'VIDEO_ANALYSIS_METRICS_END' in stripped:
            html_parts.append('<div class="metrics-footer">— Конец машиночитаемых данных —</div>')
            continue
        
        # Oddiy paragraf
        html_parts.append(f'<p>{process_inline_formatting(stripped)}</p>')
    
    # Qolgan jadval/list/code block
    if in_table:
        html_parts.append(format_table(table_lines))
    if in_list:
        html_parts.append(format_list(list_items))
    if in_code_block:
        html_parts.append(format_code_block(code_block_lines, code_block_lang))
    
    return '\n'.join(html_parts)


def format_code_block(lines: list, lang: str = "") -> str:
    """Code block ni HTML ga aylantirish - JSON uchun jadval ko'rinishida"""
    if not lines:
        return ""
    
    code_content = '\n'.join(lines)
    
    # JSON uchun maxsus - jadvalga aylantirish
    if lang == "json":
        try:
            import json
            parsed = json.loads(code_content)
            
            # Machine data JSON ekanligini aniqlash
            if isinstance(parsed, dict):
                # Evaluation JSON (multi-analysis)
                if 'best_analysis' in parsed or 'analyses_comparison' in parsed:
                    return format_evaluation_json_to_table(parsed)
                
                # Machine data JSON
                if any(key in parsed for key in ['video_data', 'content_metrics', 'emotional_metrics', 'strategic_indices', 'metadata']):
                    return format_machine_data_to_table(parsed)
                
                # Oddiy JSON dict - simple table qilish
                return format_simple_json_to_table(parsed)
            
            # JSON array - oddiy ko'rsatish
            code_content = json.dumps(parsed, indent=2, ensure_ascii=False)
        except:
            pass  # JSON parse xatosi bo'lsa, original qoldirish
    
    # HTML escape
    code_content = (code_content
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
    )
    
    # Lang label
    lang_label = lang.upper() if lang else "CODE"
    
    return f'''<div class="code-block">
    <div class="code-header">{lang_label}</div>
    <pre><code>{code_content}</code></pre>
</div>'''


def format_simple_json_to_table(data: dict) -> str:
    """Oddiy JSON dict ni jadvalga aylantirish"""
    if not isinstance(data, dict):
        return ""
    
    html = ['<div class="machine-data-section">']
    html.append('<table class="metrics-table">')
    html.append('<thead><tr><th colspan="2">📊 Данные</th></tr></thead>')
    html.append('<tbody>')
    
    for key, value in data.items():
        # Keyni rus tiliga tarjima qilish
        key_label = translate_key_to_russian(key)
        
        if isinstance(value, dict):
            # Nested dict
            html.append(f'<tr><td colspan="2"><strong>{key_label}</strong></td></tr>')
            for k, v in value.items():
                k_label = translate_key_to_russian(k)
                html.append(f'<tr><td style="padding-left: 20px;">↳ {k_label}</td><td>{format_json_value(v)}</td></tr>')
        elif isinstance(value, list):
            html.append(f'<tr><td>{key_label}</td><td>{", ".join(str(v) for v in value)}</td></tr>')
        else:
            html.append(f'<tr><td>{key_label}</td><td>{format_json_value(value)}</td></tr>')
    
    html.append('</tbody></table></div>')
    return '\n'.join(html)


def translate_key_to_russian(key: str) -> str:
    """JSON keylarini rus tiliga tarjima qilish"""
    translations = {
        # Video data
        'title': 'Название',
        'channel': 'Канал',
        'duration': 'Длительность',
        'views': 'Просмотры',
        'likes': 'Лайки',
        'comments': 'Комментарии',
        'subscribers': 'Подписчики',
        'published': 'Дата публикации',
        'description': 'Описание',
        
        # Metrics
        'engagement_rate': 'Вовлечённость',
        'viral_coefficient': 'Виральный коэффициент',
        'content_score': 'Оценка контента',
        'quality_score': 'Качество',
        'relevance_score': 'Релевантность',
        'retention_rate': 'Удержание',
        'ctr': 'CTR (кликабельность)',
        
        # Emotional
        'emotional_tone': 'Эмоциональный тон',
        'sentiment': 'Настроение',
        'positive': 'Позитивные',
        'negative': 'Негативные',
        'neutral': 'Нейтральные',
        
        # Strategic
        'growth_potential': 'Потенциал роста',
        'monetization_index': 'Индекс монетизации',
        'audience_fit': 'Соответствие аудитории',
        'trend_alignment': 'Соответствие трендам',
        
        # General
        'score': 'Оценка',
        'value': 'Значение',
        'count': 'Количество',
        'total': 'Итого',
        'average': 'Среднее',
        'percentage': 'Процент',
        'status': 'Статус',
        'type': 'Тип',
        'name': 'Название',
        'id': 'ID',
        'date': 'Дата',
        'time': 'Время',
        
        # Analysis
        'completeness': 'Полнота',
        'structure': 'Структура',
        'depth': 'Глубина',
        'value_content': 'Ценность контента',
        'clarity': 'Ясность',
        'strengths': 'Сильные стороны',
        'weaknesses': 'Слабые стороны',
        'suggestions': 'Рекомендации',
        'best_analysis': 'Лучший анализ',
        'reason': 'Причина',
        'overall_score': 'Общая оценка',
    }
    
    # Keyni normalize qilish (snake_case -> bo'sh joy bilan)
    normalized = key.lower().replace('-', '_')
    
    if normalized in translations:
        return translations[normalized]
    
    # Topilmasa, keyni formatting qilish
    return key.replace('_', ' ').title()


def format_json_value(value) -> str:
    """JSON qiymatini chiroyli ko'rsatish"""
    if isinstance(value, bool):
        return "✓ Да" if value else "✗ Нет"
    elif isinstance(value, (int, float)):
        if isinstance(value, float):
            if value <= 1 and value >= 0:
                return f"{value * 100:.1f}%"
            return f"{value:.2f}"
        return f"{value:,}".replace(',', ' ')
    elif value is None:
        return "—"
    else:
        return str(value)


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
   CODE BLOCKS (JSON, etc.)
   ───────────────────────────────────────────────────────────────── */

.code-block {
    margin: 16px 0;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #e2e8f0;
    page-break-inside: avoid;
}

.code-header {
    background: #1e293b;
    color: #94a3b8;
    font-size: 8pt;
    font-weight: 600;
    padding: 6px 12px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

.code-block pre {
    margin: 0;
    padding: 16px;
    background: #0f172a;
    overflow-x: auto;
}

.code-block code {
    font-family: 'DejaVu Sans Mono', 'Courier New', monospace;
    font-size: 8pt;
    line-height: 1.5;
    color: #e2e8f0;
    background: transparent;
    padding: 0;
    white-space: pre-wrap;
    word-wrap: break-word;
}

/* ─────────────────────────────────────────────────────────────────
   METRICS SECTION (Machine-readable data)
   ───────────────────────────────────────────────────────────────── */

.metrics-header {
    margin-top: 30px;
    margin-bottom: 10px;
    padding: 12px 16px;
    background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%);
    color: white;
    font-size: 11pt;
    font-weight: 600;
    border-radius: 8px 8px 0 0;
    text-align: center;
}

.metrics-footer {
    margin-top: 10px;
    margin-bottom: 30px;
    padding: 8px 16px;
    background: #f1f5f9;
    color: #64748b;
    font-size: 9pt;
    font-style: italic;
    border-radius: 0 0 8px 8px;
    text-align: center;
    border-top: 2px dashed #cbd5e1;
}

/* ─────────────────────────────────────────────────────────────────
   EVALUATION SECTION (Multi-analysis comparison)
   ───────────────────────────────────────────────────────────────── */

.evaluation-section {
    margin: 20px 0;
    page-break-inside: avoid;
}

.best-analysis-box {
    background: linear-gradient(135deg, #fef3c7 0%, #fcd34d 100%);
    border: 2px solid #f59e0b;
    border-radius: 12px;
    padding: 16px;
    margin: 16px 0;
    text-align: center;
}

.best-label {
    font-size: 10pt;
    color: #92400e;
    font-weight: 600;
    text-transform: uppercase;
}

.best-id {
    font-size: 18pt;
    font-weight: 700;
    color: #78350f;
    margin: 8px 0;
}

.best-reason {
    font-size: 9pt;
    color: #92400e;
    font-style: italic;
}

.evaluation-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 8pt;
    margin: 12px 0;
}

.evaluation-table th {
    background: #1e40af;
    color: white;
    padding: 8px 4px;
    text-align: center;
    font-size: 7pt;
}

.evaluation-table td {
    border: 1px solid #e2e8f0;
    padding: 6px 4px;
    text-align: center;
}

.evaluation-table .total-score {
    background: #dbeafe;
    font-size: 9pt;
}

.evaluation-table .rank {
    font-weight: 700;
}

.evaluation-table .rank-1 {
    background: #fef3c7;
}

.evaluation-table .rank-2 {
    background: #e0e7ff;
}

.analysis-details {
    background: #f8fafc;
    border-left: 3px solid #3b82f6;
    padding: 10px 12px;
    margin: 10px 0;
    font-size: 8pt;
}

.analysis-details h4 {
    margin: 0 0 8px 0;
    color: #1e40af;
    font-size: 9pt;
}

.strengths { color: #059669; margin: 6px 0; }
.weaknesses { color: #dc2626; margin: 6px 0; }
.suggestions { color: #7c3aed; margin: 6px 0; }

.analysis-details ul {
    margin: 4px 0 4px 16px;
    padding: 0;
}

.analysis-details li {
    margin: 2px 0;
}

.comparison-summary, .overall-recommendations {
    background: #f0fdf4;
    border: 1px solid #86efac;
    border-radius: 8px;
    padding: 12px;
    margin: 12px 0;
}

.comparison-summary h4, .overall-recommendations h4 {
    margin: 0 0 8px 0;
    color: #166534;
    font-size: 10pt;
}

/* ─────────────────────────────────────────────────────────────────
   MACHINE DATA SECTION (Metrics tables)
   ───────────────────────────────────────────────────────────────── */

.machine-data-section {
    margin: 20px 0;
}

.metrics-table {
    width: 100%;
    border-collapse: collapse;
    margin: 12px 0;
    font-size: 9pt;
}

.metrics-table thead th {
    background: linear-gradient(135deg, #3b82f6 0%, #1e40af 100%);
    color: white;
    padding: 10px;
    text-align: left;
    font-size: 10pt;
}

.metrics-table td {
    border: 1px solid #e2e8f0;
    padding: 8px 10px;
}

.metrics-table tr:nth-child(even) {
    background: #f8fafc;
}

.metrics-table td:first-child {
    width: 45%;
    color: #475569;
}

.metrics-table td:last-child {
    color: #1e40af;
    font-weight: 500;
}

.key-insights {
    background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
    border: 1px solid #fbbf24;
    border-radius: 8px;
    padding: 12px 16px;
    margin: 16px 0;
}

.key-insights h3 {
    margin: 0 0 10px 0;
    color: #92400e;
    font-size: 11pt;
}

.key-insights ul {
    margin: 0;
    padding-left: 20px;
}

.key-insights li {
    margin: 6px 0;
    color: #78350f;
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
