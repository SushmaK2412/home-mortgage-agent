"""Environment-backed settings (FRED, SQLite, optional LLM provider)."""

from typing import Optional

from pydantic import BaseSettings


class Settings(BaseSettings):
    fred_api_key: str
    schedule_tz: str = "America/New_York"
    database_path: str = "data/mortgage_rates.db"

    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"

    class Config:
        env_file = ".env"
        extra = "ignore"


def get_settings() -> Settings:
    return Settings()
