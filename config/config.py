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

    SECRET_KEY: str = "shopping_website_secret"
    ALGORITHM: str = "HS256"
    TOKEN_EXPIRY_TIME: float = 30.0

    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    ML_MODEL_PATH: str = "ml/recommender.joblib"

    class Config:
        env_file = ".env"