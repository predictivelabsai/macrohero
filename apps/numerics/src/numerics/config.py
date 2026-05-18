from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CACHE_DIR = str(_PACKAGE_ROOT / ".cache" / "massive")
_ENV_FILE = str(_PACKAGE_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    massive_api_key: str | None = Field(default=None, alias="MASSIVE_API_KEY")
    massive_cache_dir: str = Field(default=_DEFAULT_CACHE_DIR, alias="MASSIVE_CACHE_DIR")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
