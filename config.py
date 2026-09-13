"""Typed config from env / .env. Priority: OS env > .env > defaults."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=Path(__file__).parent / ".env", extra="ignore")

    base_url: str = "https://dummyjson.com"
    request_timeout: int = 30
    max_retries: int = 3


def get_settings() -> Settings:
    return Settings()
