from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from typing import List

load_dotenv()  

class Config(BaseSettings):
    BOT_TOKEN: str 
    YOUTUBE_API_KEY: str
    DATABASE_URL: str
    SORT_ORDER: str  
    LOGGING: int
    ADMIN_IDS: List[int] = []  
    AI_TUNEL_API_KEY: str  
    API_KEY: str  

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
            nums = re.findall(r'\d+', admin_ids_str)
            self.ADMIN_IDS = [int(num) for num in nums if num.isdigit()]

config = Config()