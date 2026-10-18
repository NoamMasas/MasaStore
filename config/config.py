from typing import Optional

from pydantic import BaseSettings


class Config(BaseSettings):
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = "root_password"
    MYSQL_DATABASE: str = "main"
    MYSQL_HOST: str = "localhost"
    MYSQL_PORT: int = 3306
    DATABASE_URL: str = f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DATABASE}"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_TTL: int = 100
    REDIS_PASSWORD: Optional[str] = None

    SECRET_KEY: str = "shopping_website_secret"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRY_TIME: float = 30.0

    # Gemini via its OpenAI-compatible endpoint, so the openai SDK is unchanged.
    GEMINI_API_KEY: str = ""
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai/"
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    # Cloud-only daily caps that /chat/reset/ can't clear; 0 = disabled.
    CHAT_DAILY_USER_LIMIT: int = 0
    CHAT_DAILY_GLOBAL_LIMIT: int = 0

    ML_MODEL_PATH: str = "ml/recommender.joblib"

    class Config:
        env_file = ".env"