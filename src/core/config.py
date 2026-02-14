"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for API and data services."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)

    app_name: str = "NBA Stats Assistant API"
    app_env: str = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    api_prefix: str = "/v1"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/nba_stats",
        description="SQLAlchemy connection URL.",
    )
    sql_echo: bool = False

    api_key_header: str = "X-API-Key"
    default_limit: int = 50
    max_limit: int = 200
    ingest_default_season: str = "2024-25"
    ingest_max_players: int = 30
    ingest_active_only: bool = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Memoized settings getter."""

    return Settings()
