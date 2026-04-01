"""Configuration centralisée via pydantic-settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://apex:changeme@db:5432/apex_screener"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # API Keys
    fred_api_key: str = ""
    fmp_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    groq_api_key: str = ""          # ← NOUVEAU

    # App
    app_env: str = "production"
    log_level: str = "INFO"
    fastapi_port: int = 8000

    # Rate limits (seconds between requests)
    fred_rate_limit: float = 1.0
    fmp_rate_limit: float = 12.0    # FMP free = 5 req/min
    sec_rate_limit: float = 0.15    # SEC = 10 req/sec
    defillama_rate_limit: float = 1.0

    # Alert thresholds
    insider_min_amount: float = 250_000
    roic_min_threshold: float = 10.0
    crypto_mcap_fdv_min_ratio: float = 0.4
    tvl_spike_threshold: float = 20.0   # % increase

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()"""Configuration centralisée via pydantic-settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://apex:changeme@db:5432/apex_screener"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # API Keys
    fred_api_key: str = ""
    fmp_api_key: str = ""
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    groq_api_key: str = ""          # ← NOUVEAU

    # App
    app_env: str = "production"
    log_level: str = "INFO"
    fastapi_port: int = 8000

    # Rate limits (seconds between requests)
    fred_rate_limit: float = 1.0
    fmp_rate_limit: float = 12.0    # FMP free = 5 req/min
    sec_rate_limit: float = 0.15    # SEC = 10 req/sec
    defillama_rate_limit: float = 1.0

    # Alert thresholds
    insider_min_amount: float = 250_000
    roic_min_threshold: float = 10.0
    crypto_mcap_fdv_min_ratio: float = 0.4
    tvl_spike_threshold: float = 20.0   # % increase

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore",
    }


@lru_cache()
def get_settings() -> Settings:
    return Settings()
