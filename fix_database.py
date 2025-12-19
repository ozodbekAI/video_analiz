# Создайте тестовый файл test_prompts.py
import asyncio
from database.crud import check_prompts_exist

async def test():
    for analysis_type in [
        'audience_map',
        'content_prediction',
        'channel_diagnostics',
        'content_ideas',
        'viral_potential',
        'iterative_ideas'
    ]:
        result = await check_prompts_exist(analysis_type)
        print(f"\n{analysis_type}:")
        print(f"  Exists: {result['exists']}")
        print(f"  Found: {result['found']}")
        print(f"  Missing: {result['missing']}")

asyncio.run(test())