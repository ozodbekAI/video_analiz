from openai import OpenAI

from config import config

client = OpenAI(
    api_key=config.AI_TUNEL_API_KEY,
    base_url="https://api.aitunnel.ru/v1/",
)

chat_result = client.chat.completions.create(
    messages=[{"role": "user", "content": "Скажи интересный факт"}],
    model="deepseek-r1",
    max_tokens=50000, 
)
print(chat_result.choices[0].message)

