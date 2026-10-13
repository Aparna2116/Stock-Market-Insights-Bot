"""Configuration settings for Stock Market Insights Bot."""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    # App Mode
    DEMO_MODE: bool = True
    APP_NAME: str = "Stock Market Insights Bot"
    APP_VERSION: str = "1.0.0"

    # Database
    DATABASE_URL: str = f"sqlite:///{BASE_DIR / 'data' / 'stock_insights.db'}"

    # LLM & AI
    LLM_PROVIDER: str = "rule_based"  # Options: "groq", "gemini", "openai", "rule_based"
    GROQ_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    LLM_TEMPERATURE: float = 0.1
    LLM_TIMEOUT_SECONDS: int = 20

    # Market Configuration
    DEFAULT_EXCHANGE: str = "NASDAQ"
    DEFAULT_TIMEZONE: str = "America/New_York"
    MARKET_OPEN_HOUR: int = 9
    MARKET_OPEN_MINUTE: int = 30

    # Ingestion Settings
    MAX_ARTICLES_PER_FEED: int = 20
    FETCH_TIMEOUT_SECONDS: int = 10
    NEWS_CACHE_TTL_MINUTES: int = 30

    # Logging
    LOG_LEVEL: str = "INFO"

    # Default Watchlist
    WATCHLIST: list[str] = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"
    ]

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
