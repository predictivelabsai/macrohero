"""Service-internal orchestration for the FX projection engine.

Pure numerics: builds the factor-shock projection. The LangChain @tool
wrapper lives on the TypeScript side (packages/tools); this service is a
plain HTTP function call.
"""

from __future__ import annotations

import dataclasses
from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator

from numerics.config import get_settings
from numerics.data import (
    InsufficientDataError,
    InvalidPairError,
    MassiveAPIError,
    MassiveAuthError,
    MassiveDataClient,
)
from numerics.factors import get_factor_by_name
from numerics.projection import ProjectionResult, fit_and_project

SEVERITY_MULTIPLIERS: dict[str, float] = {
    "mild": 0.5,
    "moderate": 1.0,
    "severe": 2.0,
    "extreme": 3.0,
}


Direction = Literal["up", "down"]
Severity = Literal["mild", "moderate", "severe", "extreme"]


class FactorShock(BaseModel):
    name: str
    direction: Direction = Field(
        description=(
            "Direction the factor moves under the scenario. 'up' means the"
            " factor rises; 'down' means it falls. (For yields, 'up' means"
            " yields rise — which corresponds to bond-price ETFs falling.)"
        )
    )
    severity: Severity = Field(
        description=(
            "Magnitude tier at the chosen horizon. mild=0.5*sigma, moderate=1*sigma,"
            " severe=2*sigma, extreme=3*sigma at the requested horizon."
        )
    )

    @field_validator("name")
    @classmethod
    def _name_is_known(cls, v: str) -> str:
        try:
            get_factor_by_name(v)
        except KeyError as exc:
            raise ValueError(str(exc)) from exc
        return v


class RunFactorProjectionArgs(BaseModel):
    pair: str = Field(description="FX pair, e.g. 'EUR/USD', 'USDJPY', or 'C:EURUSD'.")
    horizon_days: int = Field(ge=1, le=90)
    factors: list[FactorShock] = Field(min_length=1, max_length=8)
    regression_window_days: int = Field(default=252, ge=60, le=1000)


def _result_as_dict(result: ProjectionResult) -> dict[str, Any]:
    return {
        "pair": result.pair,
        "horizon_days": result.horizon_days,
        "regression_window_days": result.regression_window_days,
        "r_squared": result.r_squared,
        "intercept": result.intercept,
        "factors": [dataclasses.asdict(f) for f in result.factors],
        "projection": dataclasses.asdict(result.projection) if result.projection else None,
        "diagnostics": result.diagnostics,
    }


def _error_result(
    pair: str, horizon_days: int, regression_window_days: int, code: str, message: str
) -> dict[str, Any]:
    return {
        "pair": pair,
        "horizon_days": horizon_days,
        "regression_window_days": regression_window_days,
        "r_squared": 0.0,
        "intercept": 0.0,
        "factors": [],
        "projection": None,
        "diagnostics": {
            "n_observations": 0,
            "warnings": [],
            "error": {"code": code, "message": message},
        },
    }


async def run_factor_projection_impl(args: RunFactorProjectionArgs) -> dict[str, Any]:
    """Run the deterministic projection. Returns a dict, never raises."""
    settings = get_settings()
    if not settings.massive_api_key:
        return _error_result(
            args.pair,
            args.horizon_days,
            args.regression_window_days,
            "massive_unconfigured",
            "MASSIVE_API_KEY not set",
        )

    cache_dir = Path(settings.massive_cache_dir)
    client = MassiveDataClient(api_key=settings.massive_api_key, cache_dir=cache_dir)

    try:
        symbol = await client.resolve_fx_pair(args.pair)
        spot, spot_date = await client.latest_close(symbol)

        end = spot_date
        start = end - timedelta(days=int(args.regression_window_days * 1.5) + 30)

        pair_df = await client.fetch_bars(symbol, start, end)
        factor_dfs: dict[str, pd.DataFrame] = {}
        for fs in args.factors:
            spec = get_factor_by_name(fs.name)
            factor_dfs[fs.name] = await client.fetch_bars(spec.massive_ticker, start, end)
    except InvalidPairError as exc:
        return _error_result(
            args.pair, args.horizon_days, args.regression_window_days, "invalid_pair", str(exc)
        )
    except InsufficientDataError as exc:
        return _error_result(
            args.pair,
            args.horizon_days,
            args.regression_window_days,
            "insufficient_data",
            str(exc),
        )
    except MassiveAuthError as exc:
        return _error_result(
            args.pair, args.horizon_days, args.regression_window_days, "massive_auth", str(exc)
        )
    except MassiveAPIError as exc:
        return _error_result(
            args.pair, args.horizon_days, args.regression_window_days, "massive_api", str(exc)
        )

    pair_col = "__pair__"
    joined = pair_df.rename(columns={"close": pair_col})
    for name, df in factor_dfs.items():
        joined = joined.join(df.rename(columns={"close": name}), how="inner")
    joined = joined.tail(args.regression_window_days)
    if len(joined) < 61:
        return _error_result(
            args.pair,
            args.horizon_days,
            args.regression_window_days,
            "insufficient_data",
            f"only {len(joined) - 1} aligned return observations after inner-join (need >= 60)",
        )

    pair_returns = np.diff(np.log(joined[pair_col].to_numpy()))
    factor_names: list[str] = []
    factor_transforms: list[str] = []
    factor_cols: list[np.ndarray] = []
    for fs in args.factors:
        spec = get_factor_by_name(fs.name)
        series = joined[fs.name].to_numpy()
        if spec.transform == "log_return":
            col = np.diff(np.log(series))
        elif spec.transform == "abs_change_bp":
            col = np.diff(series) * 100.0
        else:
            return _error_result(
                args.pair,
                args.horizon_days,
                args.regression_window_days,
                "internal",
                f"unsupported transform {spec.transform}",
            )
        factor_names.append(fs.name)
        factor_transforms.append(spec.transform)
        factor_cols.append(col)

    factor_returns = np.column_stack(factor_cols)

    sqrt_h = float(np.sqrt(args.horizon_days))
    factor_daily_std = factor_returns.std(axis=0, ddof=1)
    expected: dict[str, float] = {}
    severities: dict[str, str] = {}
    directions: dict[str, str] = {}
    sigma_multiples: dict[str, float] = {}
    for i, fs in enumerate(args.factors):
        sigma_daily = float(factor_daily_std[i])
        sigma_horizon = sigma_daily * sqrt_h
        multiplier = SEVERITY_MULTIPLIERS[fs.severity]
        sign = 1.0 if fs.direction == "up" else -1.0
        if factor_transforms[i] == "log_return":
            expected[fs.name] = sign * multiplier * sigma_horizon * 100.0
        else:
            expected[fs.name] = sign * multiplier * sigma_horizon
        severities[fs.name] = fs.severity
        directions[fs.name] = fs.direction
        sigma_multiples[fs.name] = sign * multiplier

    result = fit_and_project(
        pair=args.pair,
        pair_returns=pair_returns,
        factor_names=factor_names,
        factor_returns=factor_returns,
        factor_transforms=factor_transforms,
        expected_factor_changes=expected,
        horizon_days=args.horizon_days,
        regression_window_days=args.regression_window_days,
        spot_at_t0=spot,
    )

    out = _result_as_dict(result)
    for fc in out["factors"]:
        name = fc["name"]
        try:
            fc["ticker"] = get_factor_by_name(name).massive_ticker
        except KeyError:
            fc["ticker"] = ""
        fc["severity"] = severities.get(name, "")
        fc["direction"] = directions.get(name, "")
        fc["sigma_multiple"] = sigma_multiples.get(name, 0.0)
    return out
