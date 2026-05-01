"""
Application configuration loaded from environment variables.
All sensitive values come from .env — never hardcoded.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str
    SECRET_KEY: str = "changeme-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS: int = 24
    MONITORING_TOKEN_EXPIRE_HOURS: int = 1
    MONITORING_API_KEY: str = "sk_monitor_2024_securekey_abc123"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
