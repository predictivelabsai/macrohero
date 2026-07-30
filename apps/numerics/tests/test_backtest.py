"""Tests for the momentum backtest engine and its route.

No network and no real Massive key: the SDK's list_aggs / list_tickers are
monkeypatched (same approach as test_data_massive.py), and get_settings is
patched to a fake key + a tmp cache dir so runs are hermetic.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from massive.exceptions import BadResponse
from massive.rest.models.aggs import Agg
from massive.rest.models.tickers import Ticker

from numerics.backtest_service import RunMomentumBacktestArgs, run_momentum_backtest_impl
from numerics.main import create_app

_DAY_MS = 86_400_000
_START_MS = 1_704_067_200_000  # 2024-01-01T00:00:00Z


def _make_ohlc_agg(open_: float, high: float, low: float, close: float, ts: int) -> Agg:
    a = Agg()
    a.open = open_
    a.high = high
    a.low = low
    a.close = close
    a.timestamp = ts
    return a


def _make_ticker(sym: str) -> Ticker:
    t = Ticker()
    t.ticker = sym
    t.active = True
    return t


def _bad_response(status: int) -> BadResponse:
    exc = BadResponse(f"HTTP {status}")
    exc.http_status = status  # type: ignore[attr-defined]
    return exc


def _uptrend(n: int, slope: float = 0.002, base: float = 1.1000) -> list[Agg]:
    """A steady uptrend: momentum clears the threshold and longs hit take-profit."""
    aggs = []
    for k in range(n):
        close = base + k * slope
        ts = _START_MS + k * _DAY_MS
        aggs.append(_make_ohlc_agg(close, close + 0.0005, close - 0.0005, close, ts))
    return aggs


@pytest.fixture
def fake_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Patch get_settings so the engine uses a fake key and an isolated cache."""
    fake = SimpleNamespace(massive_api_key="test_key", massive_cache_dir=str(tmp_path))
    monkeypatch.setattr("numerics.backtest_service.get_settings", lambda: fake)
    return fake


def _patch_market(monkeypatch: pytest.MonkeyPatch, aggs: list[Agg], ticker: str = "C:EURUSD"):
    monkeypatch.setattr(
        "massive.RESTClient.list_tickers",
        lambda self, ticker=None, market=None, active=None, **kw: iter([_make_ticker(ticker)]),
    )
    monkeypatch.setattr(
        "massive.RESTClient.list_aggs",
        lambda self, t, mult, span, frm, to, **kw: iter(aggs),
    )


# --------------------------------------------------------------- service tests

async def test_momentum_happy_path(fake_settings, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_market(monkeypatch, _uptrend(60))

    result = await run_momentum_backtest_impl(
        RunMomentumBacktestArgs(pair="EUR/USD", lookback=20, take_profit=1.0, stop_loss=0.5)
    )

    assert result["diagnostics"]["error"] is None
    assert result["pair"] == "C:EURUSD"
    assert result["strategy"] == "momentum"
    m = result["metrics"]
    assert m["total_trades"] > 0
    assert m["total_trades"] == len(result["trades"])
    # A pure uptrend with these brackets only opens longs and they win.
    assert all(t["direction"] == "long" for t in result["trades"])
    assert m["win_rate"] == 100.0
    assert m["total_return"] > 0
    # First long should take profit, not stop out.
    assert result["trades"][0]["hit_target"] is True


async def test_momentum_forwards_params(fake_settings, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_market(monkeypatch, _uptrend(60))
    result = await run_momentum_backtest_impl(RunMomentumBacktestArgs(pair="EURUSD"))
    # Defaults from the args model are echoed back for the caller.
    assert result["params"]["lookback"] == 20
    assert result["params"]["initial_capital"] == 100_000
    assert result["params"]["take_profit"] == 1.0


async def test_momentum_insufficient_data_envelope(
    fake_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_market(monkeypatch, _uptrend(12))  # < lookback + 5

    result = await run_momentum_backtest_impl(RunMomentumBacktestArgs(pair="EURUSD", lookback=20))
    assert result["metrics"] is None
    assert result["trades"] == []
    assert result["diagnostics"]["error"]["code"] == "insufficient_data"


async def test_momentum_invalid_pair_envelope(
    fake_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "massive.RESTClient.list_tickers",
        lambda self, ticker=None, market=None, active=None, **kw: iter([]),
    )
    result = await run_momentum_backtest_impl(RunMomentumBacktestArgs(pair="ZZZZZZ"))
    assert result["metrics"] is None
    assert result["diagnostics"]["error"]["code"] == "invalid_pair"


async def test_momentum_auth_error_envelope(
    fake_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    def boom(self, ticker=None, market=None, active=None, **kw):
        raise _bad_response(401)

    monkeypatch.setattr("massive.RESTClient.list_tickers", boom)
    result = await run_momentum_backtest_impl(RunMomentumBacktestArgs(pair="EURUSD"))
    assert result["diagnostics"]["error"]["code"] == "massive_auth"


async def test_momentum_unconfigured_key(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = SimpleNamespace(massive_api_key=None, massive_cache_dir="/tmp/x")
    monkeypatch.setattr("numerics.backtest_service.get_settings", lambda: fake)

    result = await run_momentum_backtest_impl(RunMomentumBacktestArgs(pair="EURUSD"))
    assert result["diagnostics"]["error"]["code"] == "massive_unconfigured"


# ----------------------------------------------------------------- route tests

def test_route_momentum_happy_path(fake_settings, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_market(monkeypatch, _uptrend(60))
    client = TestClient(create_app())

    resp = client.post("/v1/backtest/momentum", json={"pair": "EUR/USD", "lookback": 20})
    assert resp.status_code == 200
    body = resp.json()
    assert body["diagnostics"]["error"] is None
    assert body["metrics"]["total_trades"] > 0


def test_route_momentum_insufficient_data_is_200_envelope(
    fake_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_market(monkeypatch, _uptrend(12))
    client = TestClient(create_app())

    resp = client.post("/v1/backtest/momentum", json={"pair": "EURUSD", "lookback": 20})
    # Domain error is an envelope, not an HTTP error (matches /v1/projection).
    assert resp.status_code == 200
    assert resp.json()["diagnostics"]["error"]["code"] == "insufficient_data"


def test_route_momentum_validation_is_422(fake_settings) -> None:
    client = TestClient(create_app())
    # lookback below the allowed floor -> Pydantic 422, not an envelope.
    resp = client.post("/v1/backtest/momentum", json={"pair": "EURUSD", "lookback": 1})
    assert resp.status_code == 422


def test_route_momentum_requires_pair(fake_settings) -> None:
    client = TestClient(create_app())
    resp = client.post("/v1/backtest/momentum", json={})
    assert resp.status_code == 422


# ------------------------------------------------------------- units + symbol

async def test_trades_include_units_and_symbol(
    fake_settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_market(monkeypatch, _uptrend(60))
    result = await run_momentum_backtest_impl(RunMomentumBacktestArgs(pair="EUR/USD"))

    assert result["trades"], "expected at least one trade"
    for t in result["trades"]:
        assert "units" in t and isinstance(t["units"], float)
        assert t["units"] > 0
        assert t["symbol"] == "C:EURUSD"
    # Existing keys are still present (additive change).
    first = result["trades"][0]
    for key in ("entry_date", "exit_date", "direction", "pnl", "capital_after"):
        assert key in first


# ------------------------------------------------------------- period alias

def test_period_maps_to_history_days() -> None:
    assert RunMomentumBacktestArgs(pair="EURUSD", period="3mo").history_days == 90
    assert RunMomentumBacktestArgs(pair="EURUSD", period="6mo").history_days == 180
    assert RunMomentumBacktestArgs(pair="EURUSD", period="1y").history_days == 365
    assert RunMomentumBacktestArgs(pair="EURUSD", period="2y").history_days == 730


def test_explicit_history_days_wins_over_period() -> None:
    # period is sugar; an explicit history_days must not be overwritten.
    args = RunMomentumBacktestArgs(pair="EURUSD", period="2y", history_days=500)
    assert args.history_days == 500


def test_no_period_keeps_default_history_days() -> None:
    assert RunMomentumBacktestArgs(pair="EURUSD").history_days == 365


def test_route_accepts_period(fake_settings, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_market(monkeypatch, _uptrend(60))
    client = TestClient(create_app())
    resp = client.post("/v1/backtest/momentum", json={"pair": "EUR/USD", "period": "6mo"})
    assert resp.status_code == 200
    assert resp.json()["params"]["history_days"] == 180


# ----------------------------------------------------------------- catalog

def test_catalog_shape(fake_settings) -> None:
    client = TestClient(create_app())
    resp = client.get("/v1/catalog")
    assert resp.status_code == 200
    body = resp.json()

    assert body["strategies"] == ["momentum"]
    assert body["pairs"] == ["EUR/USD", "GBP/USD", "USD/JPY", "USD/CHF", "AUD/USD", "USD/CAD"]

    params = body["params"]
    assert set(params) == {
        "history_days",
        "lookback",
        "momentum_threshold",
        "take_profit",
        "stop_loss",
        "position_size_pct",
    }
    # Ranges come straight from the model's Field constraints.
    assert params["history_days"] == {"min": 30, "max": 2000, "default": 365}
    assert params["lookback"] == {"min": 5, "max": 60, "default": 20}
    assert params["momentum_threshold"] == {"min": 0, "max": 10, "default": 0.5}
    assert params["take_profit"] == {"min": 0, "max": 10, "default": 1.0}
    assert params["stop_loss"] == {"min": 0, "max": 10, "default": 0.5}
    assert params["position_size_pct"] == {"min": 0, "max": 100, "default": 10}


# -------------------------------------------------------------- service auth

def _patch_service_key(monkeypatch: pytest.MonkeyPatch, key: str | None) -> None:
    fake = SimpleNamespace(
        numerics_service_key=key, massive_api_key="k", massive_cache_dir="/tmp/x"
    )
    monkeypatch.setattr("numerics.routes.get_settings", lambda: fake)


def test_auth_allows_all_when_key_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_service_key(monkeypatch, None)
    client = TestClient(create_app())
    assert client.get("/v1/catalog").status_code == 200


def test_auth_rejects_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_service_key(monkeypatch, "s3cret")
    client = TestClient(create_app())
    resp = client.get("/v1/catalog")
    assert resp.status_code == 401


def test_auth_rejects_wrong_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_service_key(monkeypatch, "s3cret")
    client = TestClient(create_app())
    resp = client.get("/v1/catalog", headers={"X-Service-Key": "nope"})
    assert resp.status_code == 401


def test_auth_accepts_correct_key(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_service_key(monkeypatch, "s3cret")
    client = TestClient(create_app())
    resp = client.get("/v1/catalog", headers={"X-Service-Key": "s3cret"})
    assert resp.status_code == 200


def test_healthz_never_gated(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_service_key(monkeypatch, "s3cret")
    client = TestClient(create_app())
    # /healthz is open even when the service key is set and no header is sent.
    assert client.get("/healthz").status_code == 200
