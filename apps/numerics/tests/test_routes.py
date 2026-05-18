from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from numerics.factors import FACTOR_UNIVERSE
from numerics.main import app


def _bar_df(start: date, n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start=start, periods=n, freq="D")
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    return pd.DataFrame({"close": closes}, index=idx)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_healthz_returns_ok(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_factors_returns_universe(client: TestClient) -> None:
    response = client.get("/v1/factors")
    assert response.status_code == 200
    data = response.json()
    assert "factors" in data
    assert isinstance(data["factors"], list)
    assert len(data["factors"]) == len(FACTOR_UNIVERSE)

    # Each entry has the fields TS codegen expects.
    sample = data["factors"][0]
    assert {"name", "massive_ticker", "asset_class", "description", "transform"} <= set(sample)


def test_factors_response_matches_universe_order(client: TestClient) -> None:
    response = client.get("/v1/factors")
    names = [f["name"] for f in response.json()["factors"]]
    expected_names = [f.name for f in FACTOR_UNIVERSE]
    assert names == expected_names


@pytest.fixture
def fake_massive(monkeypatch, tmp_path: Path):
    """Wire fake Massive responses so the projection endpoint can run end-to-end."""
    pair_df = _bar_df(date(2024, 1, 1), 260, seed=10)
    brent_df = _bar_df(date(2024, 1, 1), 260, seed=11)

    from numerics.data import MassiveDataClient

    async def fake_resolve(_self, _pair: str) -> str:
        return "C:EURUSD"

    async def fake_fetch_bars(_self, symbol: str, _start: date, _end: date) -> pd.DataFrame:
        return pair_df if symbol == "C:EURUSD" else brent_df

    async def fake_latest_close(_self, _symbol: str) -> tuple[float, date]:
        return float(pair_df["close"].iloc[-1]), date(2024, 9, 17)

    monkeypatch.setattr(MassiveDataClient, "resolve_fx_pair", fake_resolve)
    monkeypatch.setattr(MassiveDataClient, "fetch_bars", fake_fetch_bars)
    monkeypatch.setattr(MassiveDataClient, "latest_close", fake_latest_close)
    monkeypatch.setenv("MASSIVE_API_KEY", "test_key")
    monkeypatch.setenv("MASSIVE_CACHE_DIR", str(tmp_path))

    from numerics.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]
    yield


def test_projection_happy_path(client: TestClient, fake_massive) -> None:
    response = client.post(
        "/v1/projection",
        json={
            "pair": "EUR/USD",
            "horizon_days": 14,
            "factors": [{"name": "Brent crude", "direction": "down", "severity": "severe"}],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pair"] == "EUR/USD"
    assert data["horizon_days"] == 14
    assert data["projection"] is not None
    assert data["diagnostics"]["error"] is None
    assert len(data["factors"]) == 1


def test_projection_rejects_unknown_factor(client: TestClient, fake_massive) -> None:
    response = client.post(
        "/v1/projection",
        json={
            "pair": "EUR/USD",
            "horizon_days": 14,
            "factors": [{"name": "Not A Factor", "direction": "down", "severity": "severe"}],
        },
    )
    # Pydantic validation failure -> 422 from FastAPI.
    assert response.status_code == 422


def test_projection_rejects_horizon_out_of_range(client: TestClient, fake_massive) -> None:
    response = client.post(
        "/v1/projection",
        json={
            "pair": "EUR/USD",
            "horizon_days": 0,
            "factors": [{"name": "Brent crude", "direction": "down", "severity": "severe"}],
        },
    )
    assert response.status_code == 422


def test_projection_returns_error_envelope_when_pair_invalid(
    client: TestClient, monkeypatch, tmp_path: Path
) -> None:
    from numerics.data import InvalidPairError, MassiveDataClient

    async def fake_resolve(_self, _pair: str) -> str:
        raise InvalidPairError("nope")

    monkeypatch.setattr(MassiveDataClient, "resolve_fx_pair", fake_resolve)
    monkeypatch.setenv("MASSIVE_API_KEY", "test_key")
    monkeypatch.setenv("MASSIVE_CACHE_DIR", str(tmp_path))

    from numerics.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    response = client.post(
        "/v1/projection",
        json={
            "pair": "XXX/YYY",
            "horizon_days": 14,
            "factors": [{"name": "Brent crude", "direction": "down", "severity": "mild"}],
        },
    )
    # The impl returns a structured error in the body, not an HTTP error.
    assert response.status_code == 200
    data = response.json()
    assert data["projection"] is None
    assert data["diagnostics"]["error"] is not None
    assert data["diagnostics"]["error"]["code"] == "invalid_pair"
