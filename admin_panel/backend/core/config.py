# backend/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "admin123"
    ADMIN_TOKEN: str = "SUPER_SECRET_TOKEN"

settings = Settings()
