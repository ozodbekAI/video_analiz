from openai import OpenAI, AsyncOpenAI
from config import Config
import re

config = Config()
AI_TUNEL_API_BASE = "https://api.aitunnel.ru/v1/" 

client = AsyncOpenAI(
    api_key=config.AI_TUNEL_API_KEY,
    base_url=AI_TUNEL_API_BASE,
)

def sanitize_comments(comments_text: str, max_length: int = 6000) -> str:
    lines = comments_text.split('\n')
    unique_lines = []
    seen = set()
    for line in lines:
        line_hash = hash(line.strip())
        if line_hash not in seen and len(line) > 10:  
            unique_lines.append(line)
            seen.add(line_hash)
    sanitized = '\n'.join(unique_lines[:200])  
    
    if re.search(r'(?i)(kill|death|violence|explicit)', sanitized):
        sanitized = f"[NOTE: Contains sensitive topics - analyzing neutrally]\n{sanitized}"
    return sanitized[:max_length]


async def analyze_comments_with_prompt(comments_text: str, prompt_text: str):

    try:
        clean_comments = sanitize_comments(comments_text)
        
        response = await client.chat.completions.create(
            model="deepseek-r1",
            messages=[
                {"role": "system", "content": f"{prompt_text}"},
                {"role": "user", "content": clean_comments}
            ],
            max_tokens=3000,
            temperature=0.3
        )
        
        raw_content = response.choices[0].message.content

        
        return raw_content
        
    except Exception as e:
        return "Анализ недоступен из-за технических ограничений или чувствительного контента. Рекомендуем выбрать другое видео."