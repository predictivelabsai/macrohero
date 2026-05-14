from pathlib import Path

from macrohero.config import Settings


def test_massive_settings_defaults(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.test")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.test/.well-known/jwks.json")
    monkeypatch.setenv("MASSIVE_API_KEY", "test_key_123")
    monkeypatch.setenv("MASSIVE_CACHE_DIR", str(tmp_path / "massive"))

    # _env_file=None bypasses the local .env so the test isn't sensitive to
    # whatever the developer has configured in their shell.
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.massive_api_key == "test_key_123"
    assert settings.massive_cache_dir == str(tmp_path / "massive")


def test_massive_settings_optional_default(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.test")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.test/.well-known/jwks.json")
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("MASSIVE_CACHE_DIR", raising=False)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.massive_api_key is None
    # Default is absolute path inside api/
    assert Path(settings.massive_cache_dir).is_absolute()
    assert settings.massive_cache_dir.endswith(".cache/massive")
