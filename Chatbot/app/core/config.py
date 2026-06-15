"""
Configuration centralisée — MySQL local
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="backend/.env",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM
    LLM_PROVIDER: str = "genai"
    GENAI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    ANTHROPIC_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ML
    ML_MODEL: Literal["random_forest", "gradient_boosting", "xgboost", "auto"] = "auto"

    # RAG
    TOP_K: int = 5
    EMBEDDING_METHOD: Literal["tfidf", "bm25", "sentence_transformers"] = "tfidf"

    # MySQL
    MYSQL_HOST: str = ""
    MYSQL_PORT: int = 3306
    MYSQL_DATABASE: str = ""
    MYSQL_USER: str = ""
    MYSQL_PASSWORD: str = ""

    # Redis
    REDIS_URL: str = ""
    CACHE_TTL_HOURS: int = 2
    MEMORY_ENABLED: bool = True

    # CSV
    MAX_CSV_SIZE_MB: int = 50

    # JWT
    JWT_SECRET_KEY: str = "changez-cette-valeur-en-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480


@lru_cache()
def get_settings() -> Settings:
    return Settings()