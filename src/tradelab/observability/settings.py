"""Application settings loaded from environment."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://tradelab:tradelab@localhost:5432/tradelab"
    data_root: Path = Path("./data")
    demo_mode: bool = True
    # DeepSeek (OpenAI-compatible). Override via .env
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-v4-flash"
    # Set false behind corporate SSL interception (dev only)
    llm_ssl_verify: bool = True
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    code_version: str = "0.1.0"


@lru_cache
def get_settings() -> Settings:
    return Settings()
