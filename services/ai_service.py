from openai import AsyncOpenAI
from config import Config
import re

config = Config()
AI_TUNEL_API_BASE = "https://api.aitunnel.ru/v1/" 

client = AsyncOpenAI(
    api_key=config.AI_TUNEL_API_KEY,
    base_url=AI_TUNEL_API_BASE,
)


import os
from pathlib import Path
from datetime import datetime

def save_ai_interaction(user_id: int, video_id: str, stage: str, request_text: str, response_text: str):
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

def sanitize_comments(comments_text: str, max_length: int = 8000) -> str:

    lines = comments_text.split('\n')
    unique_lines = []
    seen = set()
    
    for line in lines:
        line_hash = hash(line.strip())
        if line_hash not in seen and len(line) > 10:
            unique_lines.append(line)
            seen.add(line_hash)
    
    sanitized = '\n'.join(unique_lines[:300]) 
    
    if re.search(r'(?i)(kill|death|violence|explicit)', sanitized):
        sanitized = f"[NOTE: Contains sensitive topics - analyzing neutrally]\n{sanitized}"
    
    return sanitized[:max_length]


async def analyze_comments_with_prompt(comments_text: str, prompt_text: str, max_tokens: int = 3000) -> str:
    max_tokens: int = 3000
    try:
        clean_comments = sanitize_comments(comments_text)
        
        response = await client.chat.completions.create(
            model="deepseek-r1",
            messages=[
                {"role": "system", "content": prompt_text},
                {"role": "user", "content": clean_comments}
            ],
            max_tokens=max_tokens,
            temperature=0.3
        )
        
        raw_content = response.choices[0].message.content

        if '<think>' in raw_content and '</think>' in raw_content:
            raw_content = re.sub(r'<think>.*?</think>', '', raw_content, flags=re.DOTALL)
        
        return raw_content.strip()
        
    except Exception as e:
        error_msg = str(e)
        
        if 'insufficient_quota' in error_msg or 'quota' in error_msg.lower():
            return "⚠️ **Анализ временно недоступен**\n\nAPI квота исчерпана. Попробуйте позже или обратитесь к администратору."
        
        return f"❌ **Ошибка анализа**\n\n{error_msg[:200]}\n\nПопробуйте выбрать другое видео или обратитесь в поддержку."


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
        comments_text,
        prompt_text,
        max_tokens=max_tokens
    )