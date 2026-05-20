from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from numerics.projection_service import (
    SEVERITY_MULTIPLIERS,
    FactorShock,
    RunFactorProjectionArgs,
    run_factor_projection_impl,
)


def _bar_df(start: date, n: int, seed: int) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.date_range(start=start, periods=n, freq="D")
    closes = 100.0 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))
    return pd.DataFrame({"close": closes}, index=idx)


def test_args_validate_horizon_and_factor_count() -> None:
    with pytest.raises(ValueError):
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=0,
            factors=[FactorShock(name="Brent crude", direction="down", severity="severe")],
        )
    with pytest.raises(ValueError):
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=200,
            factors=[FactorShock(name="Brent crude", direction="down", severity="severe")],
        )
    with pytest.raises(ValueError):
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            factors=[
                FactorShock(name="Brent crude", direction="up", severity="mild") for _ in range(9)
            ],
        )


def test_args_rejects_unknown_factor_name() -> None:
    with pytest.raises(ValueError):
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            factors=[
                FactorShock(name="Definitely Not A Factor", direction="up", severity="mild")
            ],
        )


def test_args_rejects_invalid_direction_or_severity() -> None:
    with pytest.raises(ValueError):
        FactorShock(name="Brent crude", direction="sideways", severity="severe")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        FactorShock(name="Brent crude", direction="up", severity="catastrophic")  # type: ignore[arg-type]


def test_severity_multipliers_are_calibrated() -> None:
    assert SEVERITY_MULTIPLIERS["mild"] == 0.5
    assert SEVERITY_MULTIPLIERS["moderate"] == 1.0
    assert SEVERITY_MULTIPLIERS["severe"] == 2.0
    assert SEVERITY_MULTIPLIERS["extreme"] == 3.0


def _wire_fakes(
    monkeypatch, tmp_path: Path, pair_df: pd.DataFrame, factor_df: pd.DataFrame
) -> None:
    from numerics.data import MassiveDataClient

    async def fake_resolve(_self, _pair: str) -> str:
        return "C:EURUSD"

    async def fake_fetch_bars(_self, symbol: str, _start: date, _end: date) -> pd.DataFrame:
        return pair_df if symbol == "C:EURUSD" else factor_df

    async def fake_latest_close(_self, _symbol: str) -> tuple[float, date]:
        return float(pair_df["close"].iloc[-1]), date(2024, 9, 17)

    monkeypatch.setattr(MassiveDataClient, "resolve_fx_pair", fake_resolve)
    monkeypatch.setattr(MassiveDataClient, "fetch_bars", fake_fetch_bars)
    monkeypatch.setattr(MassiveDataClient, "latest_close", fake_latest_close)
    monkeypatch.setenv("MASSIVE_API_KEY", "test_key")
    monkeypatch.setenv("MASSIVE_CACHE_DIR", str(tmp_path))

    from numerics.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_happy_path(monkeypatch, tmp_path: Path) -> None:
    pair_df = _bar_df(date(2024, 1, 1), 260, seed=1)
    brent_df = _bar_df(date(2024, 1, 1), 260, seed=2)
    _wire_fakes(monkeypatch, tmp_path, pair_df, brent_df)

    args = RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=14,
        factors=[FactorShock(name="Brent crude", direction="down", severity="severe")],
    )
    result = await run_factor_projection_impl(args)
    assert result["pair"] == "EUR/USD"
    assert result["horizon_days"] == 14
    assert result["projection"] is not None
    assert result["diagnostics"]["error"] is None
    assert len(result["factors"]) == 1
    fc = result["factors"][0]
    assert fc["severity"] == "severe"
    assert fc["direction"] == "down"
    assert fc["sigma_multiple"] == pytest.approx(-2.0)
    assert fc["expected_change"] < 0
    assert 3.0 < abs(fc["expected_change"]) < 15.0


@pytest.mark.asyncio
async def test_severity_multiplier_scales_expected_change(monkeypatch, tmp_path: Path) -> None:
    pair_df = _bar_df(date(2024, 1, 1), 260, seed=3)
    brent_df = _bar_df(date(2024, 1, 1), 260, seed=4)
    _wire_fakes(monkeypatch, tmp_path, pair_df, brent_df)

    args_moderate = RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=14,
        factors=[FactorShock(name="Brent crude", direction="down", severity="moderate")],
    )
    args_severe = RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=14,
        factors=[FactorShock(name="Brent crude", direction="down", severity="severe")],
    )
    r_mod = await run_factor_projection_impl(args_moderate)
    r_sev = await run_factor_projection_impl(args_severe)
    ec_mod = r_mod["factors"][0]["expected_change"]
    ec_sev = r_sev["factors"][0]["expected_change"]
    assert ec_sev == pytest.approx(2.0 * ec_mod, rel=1e-9)


@pytest.mark.asyncio
async def test_direction_flips_sign(monkeypatch, tmp_path: Path) -> None:
    pair_df = _bar_df(date(2024, 1, 1), 260, seed=5)
    brent_df = _bar_df(date(2024, 1, 1), 260, seed=6)
    _wire_fakes(monkeypatch, tmp_path, pair_df, brent_df)

    args_up = RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=14,
        factors=[FactorShock(name="Brent crude", direction="up", severity="severe")],
    )
    args_down = RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=14,
        factors=[FactorShock(name="Brent crude", direction="down", severity="severe")],
    )
    r_up = await run_factor_projection_impl(args_up)
    r_dn = await run_factor_projection_impl(args_down)
    assert r_up["factors"][0]["expected_change"] == pytest.approx(
        -r_dn["factors"][0]["expected_change"], rel=1e-9
    )


@pytest.mark.asyncio
async def test_invalid_pair_returns_error_diagnostics(monkeypatch, tmp_path: Path) -> None:
    from numerics.data import InvalidPairError, MassiveDataClient

    async def fake_resolve(_self, _pair: str) -> str:
        raise InvalidPairError("nope")

    monkeypatch.setattr(MassiveDataClient, "resolve_fx_pair", fake_resolve)
    monkeypatch.setenv("MASSIVE_API_KEY", "test_key")
    monkeypatch.setenv("MASSIVE_CACHE_DIR", str(tmp_path))

    from numerics.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    args = RunFactorProjectionArgs(
        pair="XXX/YYY",
        horizon_days=14,
        factors=[FactorShock(name="Brent crude", direction="down", severity="mild")],
    )
    result = await run_factor_projection_impl(args)
    assert result["projection"] is None
    assert result["diagnostics"]["error"] is not None
    assert result["diagnostics"]["error"]["code"] == "invalid_pair"


@pytest.mark.asyncio
async def test_missing_api_key_returns_error(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("MASSIVE_API_KEY", raising=False)
    monkeypatch.setenv("MASSIVE_CACHE_DIR", str(tmp_path))

    from numerics.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    args = RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=14,
        factors=[FactorShock(name="Brent crude", direction="down", severity="mild")],
    )
    result = await run_factor_projection_impl(args)
    assert result["projection"] is None
    assert result["diagnostics"]["error"]["code"] == "massive_unconfigured"
