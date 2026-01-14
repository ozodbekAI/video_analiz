from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from typing import List

load_dotenv()


class Config(BaseSettings):
    """Project settings.

    Note: Web Admin (FastAPI) uses only DATABASE_URL, so most fields have safe defaults.
    The Telegram bot validates required fields at startup.
    """

    BOT_TOKEN: str = ""
    YOUTUBE_API_KEY: str = ""
    DATABASE_URL: str = "sqlite+aiosqlite:///./andrey.db"

    SORT_ORDER: str = "ASC"
    LOGGING: int = 1

    # Optional keys (may be empty when running only Web Admin)
    ADMIN_IDS: List[int] = []
    AI_TUNEL_API_KEY: str = ""
    API_KEY: str = ""

    DEFAULT_ANALYSES_LIMIT: int = 5
    MONTHLY_RESET_DAYS: int = 30

    class Config:
        env_file = ".env"
        extra = "ignore"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        admin_ids_str = os.getenv("ADMIN_IDS", "")
        if admin_ids_str:
            import re

            nums = re.findall(r"\d+", admin_ids_str)
            self.ADMIN_IDS = [int(num) for num in nums if num.isdigit()]


config = Config()
