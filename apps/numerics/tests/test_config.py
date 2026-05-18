from pathlib import Path

from numerics.config import Settings


def test_settings_reads_massive_env_vars(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("MASSIVE_API_KEY", "test_key_123")
    monkeypatch.setenv("MASSIVE_CACHE_DIR", str(tmp_path / "massive"))

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.massive_api_key == "test_key_123"
    assert settings.massive_cache_dir == str(tmp_path / "massive")


def test_settings_defaults_when_unset(monkeypatch) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.delenv("MASSIVE_CACHE_DIR", raising=False)

    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.massive_api_key is None
    assert Path(settings.massive_cache_dir).is_absolute()
    assert settings.massive_cache_dir.endswith(".cache/massive")


def test_get_settings_is_cached() -> None:
    from numerics.config import get_settings

    a = get_settings()
    b = get_settings()
    assert a is b
