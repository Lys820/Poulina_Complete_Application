"""
Configuration centralisée
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Provider
    LLM_PROVIDER: str = "gemini"

    # API Keys
    GENAI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash-lite"
    ANTHROPIC_API_KEY: str = ""
    MISTRAL_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ML Model
    ML_MODEL: Literal["random_forest", "gradient_boosting", "xgboost", "auto"] = "auto"

    # RAG
    TOP_K: int = 5
    EMBEDDING_METHOD: Literal["tfidf", "bm25", "sentence_transformers"] = "tfidf"

    # SQL Server — chaîne de connexion ODBC complète
    SQLSERVER_CONNECTION_STRING: str = (
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "Server=localhost;"
        "Database=PouleLabDB;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    # Redis
    REDIS_URL: str = ""
    CACHE_TTL_HOURS: int = 2
    MEMORY_ENABLED: bool = True

    # CSV Upload
    MAX_CSV_SIZE_MB: int = 50

    # JWT
    JWT_SECRET_KEY: str = "changez-cette-valeur-en-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480


@lru_cache()
def get_settings() -> Settings:
    return Settings()