from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.exceptions import TelegramBadRequest

async def safe_edit_text(
    query: CallbackQuery, 
    text: str, 
    reply_markup: InlineKeyboardMarkup = None,
    parse_mode: str = None
):
    try:
        if query.message.text or query.message.caption:
            await query.message.edit_text(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await query.message.delete()
            await query.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            pass
        elif "there is no text in the message" in str(e).lower():
            try:
                await query.message.delete()
            except:
                pass
            await query.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
        else:
            await query.message.answer(
                text=text,
                reply_markup=reply_markup,
                parse_mode=parse_mode
            )
    except Exception as e:
        print(f"Error in safe_edit_text: {e}")
        await query.message.answer(
            text=text,
            reply_markup=reply_markup,
            parse_mode=parse_mode
        )


"""
Telegram Helper Functions
HTML tozalash va formatni to'g'rilash uchun funksiyalar
"""
import re


def clean_html_for_telegram(text: str) -> str:
    if not text:
        return ""
    
    allowed_tags = ['b', 'i', 'u', 's', 'code', 'pre', 'a', 'strong', 'em', 'strike', 'del']
    
    def replace_tag(match):
        full_tag = match.group(0)
        tag_name = match.group(1).lower()
        

        if tag_name in allowed_tags:
            return full_tag

        return ''
    
    pattern = r'</?(\w+)[^>]*>'
    text = re.sub(pattern, replace_tag, text)
    
    text = text.replace('<strong>', '<b>').replace('</strong>', '</b>')
    text = text.replace('<em>', '<i>').replace('</em>', '</i>')
    text = text.replace('<strike>', '<s>').replace('</strike>', '</s>')
    text = text.replace('<del>', '<s>').replace('</del>', '</s>')

    text = fix_unclosed_tags(text)

    if len(text) > 4000:
        text = text[:3950] + "\n\n<i>... (текст обрезан из-за ограничения Telegram)</i>"
    
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def fix_unclosed_tags(text: str) -> str:

    stack = []
    result = []
    
    pattern = r'(</?[bius]>|</?code>|</?pre>)'
    parts = re.split(pattern, text)
    
    for part in parts:
        if not part:
            continue
        
        if part.startswith('<') and not part.startswith('</'):
            tag_name = part[1:-1]
            stack.append(tag_name)
            result.append(part)
        
        elif part.startswith('</'):
            tag_name = part[2:-1]
            if stack and stack[-1] == tag_name:
                stack.pop()
                result.append(part)

        else:
            result.append(part)

    while stack:
        tag_name = stack.pop()
        result.append(f'</{tag_name}>')
    
    return ''.join(result)


def escape_html(text: str) -> str:

    if not text:
        return ""
    
    replacements = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#39;'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    return text


def truncate_text(text: str, max_length: int = 4000, suffix: str = "...") -> str:

    if len(text) <= max_length:
        return text

    truncated = text[:max_length - len(suffix)]

    last_space = truncated.rfind(' ')
    if last_space > max_length * 0.8:  
        truncated = truncated[:last_space]
    
    return truncated + suffix


def remove_markdown(text: str) -> str:

    if not text:
        return ""
    
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'__(.+?)__', r'\1', text)
    
    text = re.sub(r'\*(.+?)\*', r'\1', text)
    text = re.sub(r'_(.+?)_', r'\1', text)
    
    text = re.sub(r'`(.+?)`', r'\1', text)
    text = re.sub(r'```[\s\S]+?```', '', text)

    text = re.sub(r'^#+\s+', '', text, flags=re.MULTILINE)

    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    return text


def format_for_telegram(
    text: str,
    clean_html: bool = True,
    remove_md: bool = False,
    max_length: int = 4000
) -> str:

    if not text:
        return ""
    if remove_md:
        text = remove_markdown(text)

    if clean_html:
        text = clean_html_for_telegram(text)

    text = truncate_text(text, max_length)
    
    return text



def split_message(text: str, max_length: int = 4000) -> list[str]:

    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        if len(para) > max_length:
            sentences = re.split(r'([.!?]\s+)', para)
            
            for i in range(0, len(sentences), 2):
                sentence = sentences[i]
                if i + 1 < len(sentences):
                    sentence += sentences[i + 1]
                
                if len(current_chunk) + len(sentence) > max_length:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    current_chunk += sentence
        else:
            if len(current_chunk) + len(para) + 2 > max_length:
                chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += '\n\n'
                current_chunk += para
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks


def add_status_emoji(text: str, status: str) -> str:

    emoji_map = {
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'info': 'ℹ️',
        'processing': '⏳',
        'loading': '🔄',
        'completed': '✅',
        'failed': '❌'
    }
    
    emoji = emoji_map.get(status, '')
    
    if emoji:
        return f"{emoji} {text}"
    return text


