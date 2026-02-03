from typing import Optional
from openai import AsyncOpenAI
from config import Config
import re
import os
from pathlib import Path
from datetime import datetime

config = Config()

# =========================
# DeepSeek DIRECT API (no AI Tunnel)
# =========================
# DeepSeek API is OpenAI-compatible; base_url can be https://api.deepseek.com/v1
# Docs: https://api-docs.deepseek.com
DEEPSEEK_API_BASE = getattr(config, "DEEPSEEK_API_BASE", None) or "https://api.deepseek.com/v1"
DEEPSEEK_API_KEY = getattr(config, "DEEPSEEK_API_KEY", None)

# Model choice:
# - "deepseek-reasoner"  (reasoning)
# - "deepseek-chat"      (chat)
# Official reasoning model doc: deepseek-reasoner
DEEPSEEK_MODEL = getattr(config, "DEEPSEEK_MODEL", None) or "deepseek-reasoner"

if not DEEPSEEK_API_KEY:
    raise ValueError(
        "DEEPSEEK_API_KEY is not set. Add it to Config / env and restart the app."
    )

client = AsyncOpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_API_BASE,
)


# =========================
# AI logs
# =========================
def save_ai_interaction(
    user_id: int,
    video_id: str,
    stage: str,
    request_text: str,
    response_text: str
):
    ai_logs_dir = Path(f"ai_logs/{user_id}")
    ai_logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    request_filename = f"{stage}_request_{video_id}_{timestamp}.txt"
    request_path = ai_logs_dir / request_filename

    with open(request_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"AI REQUEST - {stage.upper()}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"User ID: {user_id}\n")
        f.write(f"Video/Channel ID: {video_id}\n")
        f.write(f"Stage: {stage}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write(f"Request Size: {len(request_text)} chars\n")
        f.write("\n" + "=" * 80 + "\n\n")
        f.write(request_text)

    response_filename = f"{stage}_response_{video_id}_{timestamp}.txt"
    response_path = ai_logs_dir / response_filename

    with open(response_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"AI RESPONSE - {stage.upper()}\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"User ID: {user_id}\n")
        f.write(f"Video/Channel ID: {video_id}\n")
        f.write(f"Stage: {stage}\n")
        f.write(f"Timestamp: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        f.write(f"Response Size: {len(response_text)} chars\n")
        f.write("\n" + "=" * 80 + "\n\n")
        f.write(response_text)

    request_size = os.path.getsize(request_path) / 1024
    response_size = os.path.getsize(response_path) / 1024

    return {
        'request_path': str(request_path),
        'response_path': str(response_path),
        'request_size': round(request_size, 2),
        'response_size': round(response_size, 2)
    }


# =========================
# Sanitization (for comments only)
# =========================
def sanitize_comments(comments_text: str, max_length: int = 8000) -> str:
    lines = comments_text.split('\n')
    unique_lines = []
    seen = set()

    for line in lines:
        s = line.strip()
        if len(s) <= 10:
            continue
        # Dedup within runtime
        line_hash = hash(s)
        if line_hash in seen:
            continue
        seen.add(line_hash)
        unique_lines.append(line)

    sanitized = '\n'.join(unique_lines[:300])

    # Neutral safety note if sensitive words
    if re.search(r'(?i)(kill|death|violence|explicit)', sanitized):
        sanitized = f"[NOTE: Contains sensitive topics - analyzing neutrally]\n{sanitized}"

    return sanitized[:max_length]


def _strip_think_tags(text: str) -> str:
    if not text:
        return ""
    if '<think>' in text and '</think>' in text:
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return text.strip()


# =========================
# Main analyzers
# =========================
async def analyze_comments_with_prompt(
    comments_text: str,
    prompt_text: str,
    max_tokens: int = 32000,
    temperature: float = 0.3,
    model: Optional[str] = None,
) -> str:
    """
    Comments analysis (sanitized input).
    Uses DeepSeek direct API via OpenAI-compatible SDK.
    """
    try:
        clean_comments = sanitize_comments(comments_text)
        
        print(f"[AI DEBUG] Sending to DeepSeek:")
        print(f"  - Model: {model or DEEPSEEK_MODEL}")
        print(f"  - Prompt length: {len(prompt_text)} chars")
        print(f"  - Comments length: {len(clean_comments)} chars")
        print(f"  - Max tokens: {max_tokens}")

        resp = await client.chat.completions.create(
            model=model or DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": clean_comments},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        msg = resp.choices[0].message
        content = (msg.content or "")
        
        # DeepSeek Reasoner returns reasoning_content separately
        # Check if model returned reasoning but empty content
        reasoning_content = getattr(msg, 'reasoning_content', None)
        
        print(f"[AI DEBUG] Response received:")
        print(f"  - Content length: {len(content)} chars")
        print(f"  - Reasoning content: {len(reasoning_content) if reasoning_content else 0} chars")
        print(f"  - First 200 chars: {content[:200] if content else 'EMPTY'}")
        
        # If content is empty but we have reasoning, there might be an issue
        if not content and reasoning_content:
            print(f"[AI WARNING] Content empty but reasoning exists! Reasoning preview: {reasoning_content[:500]}")

        # DeepSeek reasoning model can expose extra reasoning field in some SDKs;
        # we intentionally return only final content.
        content = _strip_think_tags(content)

        return content

    except Exception as e:
        error_msg = str(e)
        print(f"[AI ERROR] Exception: {error_msg}")

        if 'insufficient_quota' in error_msg or 'quota' in error_msg.lower():
            return (
                "⚠️ **Анализ временно недоступен**\n\n"
                "API квота исчерпана. Попробуйте позже или обратитесь к администратору."
            )

        return (
            "❌ **Ошибка анализа**\n\n"
            f"{error_msg[:200]}\n\n"
            "Попробуйте выбрать другое видео или обратитесь в поддержку."
        )


async def analyze_text_with_prompt(
    text: str,
    prompt_text: str,
    max_tokens: int = 2500,
    temperature: float = 0.2,
    model: Optional[str] = None,
) -> str:
    """
    Analyze arbitrary text WITHOUT sanitization.
    Required for TZ-2 evaluator prompts where we must not distort reports.
    """
    try:
        resp = await client.chat.completions.create(
            model=model or DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": text or " "},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        msg = resp.choices[0].message
        content = _strip_think_tags(msg.content or "")
        return content

    except Exception as e:
        error_msg = str(e)
        if 'insufficient_quota' in error_msg or 'quota' in error_msg.lower():
            return (
                "⚠️ **Оценка временно недоступна**\n\n"
                "API квота исчерпана. Попробуйте позже или обратитесь к администратору."
            )
        return f"❌ **Ошибка оценки**\n\n{error_msg[:200]}"


async def analyze_shorts_adaptive(
    comments_text: str,
    prompt_text: str,
    scale: str,
    level: int
) -> str:
    token_limits = {
        'small_scale': 4000,
        'medium_scale': 3500,
        'large_scale': 3000
    }
    max_tokens = token_limits.get(scale, 3000)

    return await analyze_comments_with_prompt(
        comments_text=comments_text,
        prompt_text=prompt_text,
        max_tokens=max_tokens,
        temperature=0.3,
    )
