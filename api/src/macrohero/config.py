from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_API_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CACHE_DIR = str(_API_ROOT / ".cache" / "massive")
# Absolute path so scripts and tests resolve the env file regardless of CWD —
# `env_file=".env"` was only finding it when invoked from api/.
_ENV_FILE = str(_API_ROOT / ".env")


def _ensure_async_driver(url: str) -> str:
    """Accept stock postgres URLs and rewrite them to the async driver our
    SQLAlchemy engine expects. `postgres://` and `postgresql://` (no driver
    suffix) both become `postgresql+asyncpg://`. URLs that already specify a
    driver (e.g. `postgresql+asyncpg://`, `postgresql+psycopg2://`) are
    returned unchanged."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    scheme, sep, rest = url.partition("://")
    if not sep:
        return url
    if scheme == "postgresql":
        return f"postgresql+asyncpg://{rest}"
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(..., alias="DATABASE_URL")

    @field_validator("database_url")
    @classmethod
    def _normalize_database_url(cls, v: str) -> str:
        return _ensure_async_driver(v)

    clerk_issuer: str = Field(..., alias="CLERK_ISSUER")
    clerk_jwks_url: str = Field(..., alias="CLERK_JWKS_URL")
    clerk_webhook_secret: str = Field(default="", alias="CLERK_WEBHOOK_SECRET")

    cors_origins: str = Field(default="http://localhost:3000", alias="CORS_ORIGINS")

    # DeepSeek (OpenAI-compatible API) drives the /chat assistant. Empty key
    # makes the chat endpoint refuse with a 503 so dev can still bring up the
    # rest of the API without one.
    deepseek_api_key: str = Field(default="", alias="DEEPSEEK_API_KEY")
    deepseek_model: str = Field(default="deepseek-v4-pro", alias="DEEPSEEK_MODEL")
    # A smaller/cheaper sibling of `deepseek_model`. Used for short auxiliary
    # completions (e.g. chat-session title summarization) where the pro model's
    # reasoning depth isn't worth the latency or cost.
    deepseek_flash_model: str = Field(
        default="deepseek-v4-flash", alias="DEEPSEEK_FLASH_MODEL"
    )
    deepseek_base_url: str = Field(default="https://api.deepseek.com/v1", alias="DEEPSEEK_BASE_URL")

    # Massive market data API (https://api.massive.com)
    massive_api_key: str | None = Field(default=None, alias="MASSIVE_API_KEY")
    massive_cache_dir: str = Field(default=_DEFAULT_CACHE_DIR, alias="MASSIVE_CACHE_DIR")

    # Tavily web-search API (https://tavily.com) — backs the search_current_events
    # tool the chat agent uses to ground projections in current events.
    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
