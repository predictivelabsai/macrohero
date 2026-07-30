"""Momentum FX backtest engine.

Pure numerics, same shape as the projection service: a plain async function
that returns a dict and never raises. Domain problems (unconfigured key,
invalid pair, insufficient data) come back in the ``diagnostics.error``
envelope with HTTP 200 — matching ``run_factor_projection_impl``. Pydantic
validation failures still surface as 422 at the route layer.

Price data comes from Massive (daily OHLC), consistent with the rest of the
service. This engine is stateless: it computes and returns results but does
not persist them. If a caller needs run history stored, that belongs in the
data-owning layer (the TS api), not in this compute service.

The strategy is trend-following: measure N-day momentum, enter in the
direction of the move when it clears a threshold, then exit at the first of
take-profit, stop-loss, or a fixed time cap.
"""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Any, Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, model_validator

from numerics.config import get_settings
from numerics.data import (
    InsufficientDataError,
    InvalidPairError,
    MassiveAPIError,
    MassiveAuthError,
    MassiveDataClient,
)

# How many trading days ahead an open position is allowed to run before it is
# closed at market. Matches the reference implementation.
_MAX_HOLD_BARS = 10

# Convenience aliases callers can pass as `period` instead of raw `history_days`.
_PERIOD_TO_DAYS: dict[str, int] = {"3mo": 90, "6mo": 180, "1y": 365, "2y": 730}


class RunMomentumBacktestArgs(BaseModel):
    pair: str = Field(description="FX pair, e.g. 'EUR/USD', 'USDJPY', or 'C:EURUSD'.")
    history_days: int = Field(
        default=365,
        ge=30,
        le=2000,
        description="Calendar days of history to pull and backtest over.",
    )
    lookback: int = Field(
        default=20, ge=5, le=60, description="Days used to measure momentum."
    )
    momentum_threshold: float = Field(
        default=0.5, gt=0, le=10, description="Minimum |momentum| %% to trigger an entry."
    )
    take_profit: float = Field(default=1.0, gt=0, le=10, description="Take-profit %% from entry.")
    stop_loss: float = Field(default=0.5, gt=0, le=10, description="Stop-loss %% from entry.")
    position_size_pct: float = Field(
        default=10, gt=0, le=100, description="Position size as %% of capital."
    )
    initial_capital: float = Field(default=100_000, gt=0)
    period: Literal["3mo", "6mo", "1y", "2y"] | None = Field(
        default=None,
        description=(
            "Convenience alias for history_days: 3mo=90, 6mo=180, 1y=365, 2y=730. "
            "Applied only when history_days is not explicitly set; history_days "
            "remains the canonical field."
        ),
    )

    @model_validator(mode="after")
    def _apply_period_alias(self) -> RunMomentumBacktestArgs:
        # Only sugar: if the caller passed `period` and left `history_days` at its
        # default, translate. An explicit history_days always wins.
        if self.period is not None and "history_days" not in self.model_fields_set:
            self.history_days = _PERIOD_TO_DAYS[self.period]
        return self


# FX pairs the momentum backtest supports. Small constant here; the actual
# validity check is Massive's resolve_fx_pair at call time. Consumers read this
# via GET /v1/catalog rather than hardcoding their own list.
SUPPORTED_PAIRS: tuple[str, ...] = (
    "EUR/USD",
    "GBP/USD",
    "USD/JPY",
    "USD/CHF",
    "AUD/USD",
    "USD/CAD",
)

# Numeric params exposed in the catalog, in display order. Their ranges are
# derived from the RunMomentumBacktestArgs Field constraints below — one source
# of truth, no second hardcoded copy.
_CATALOG_PARAMS: tuple[str, ...] = (
    "history_days",
    "lookback",
    "momentum_threshold",
    "take_profit",
    "stop_loss",
    "position_size_pct",
)


def _param_spec(field_name: str) -> dict[str, float | int]:
    """Read {min, max, default} for a field from its annotated-type constraints."""
    field = RunMomentumBacktestArgs.model_fields[field_name]
    spec: dict[str, float | int] = {}
    for m in field.metadata:
        if hasattr(m, "ge"):
            spec["min"] = m.ge
        if hasattr(m, "gt"):
            spec["min"] = m.gt
        if hasattr(m, "le"):
            spec["max"] = m.le
        if hasattr(m, "lt"):
            spec["max"] = m.lt
    spec["default"] = field.default
    return spec


def build_catalog() -> dict[str, Any]:
    """Discovery payload: strategies, supported pairs, and param ranges.

    Param ranges come straight from the request model's Field constraints, so
    the catalog can never drift from what the endpoint actually accepts.
    """
    return {
        "strategies": ["momentum"],
        "pairs": list(SUPPORTED_PAIRS),
        "params": {name: _param_spec(name) for name in _CATALOG_PARAMS},
    }


def _empty_metrics(initial_capital: float) -> dict[str, float | int]:
    return {
        "total_return": 0.0,
        "total_pnl": 0.0,
        "win_rate": 0.0,
        "sharpe_ratio": 0.0,
        "max_drawdown": 0.0,
        "total_trades": 0,
        "annualized_return": 0.0,
        "final_capital": initial_capital,
    }


def _calculate_metrics(trades: list[dict], initial_capital: float) -> dict[str, float | int]:
    if not trades:
        return _empty_metrics(initial_capital)

    total_pnl = sum(t["pnl"] for t in trades)
    final_capital = initial_capital + total_pnl
    total_return = (total_pnl / initial_capital) * 100
    winners = [t for t in trades if t["pnl"] > 0]
    win_rate = (len(winners) / len(trades)) * 100

    returns = [t["pnl_pct"] / 100 for t in trades]
    sharpe = (
        np.mean(returns) / np.std(returns) * np.sqrt(252)
        if len(returns) > 1 and np.std(returns) > 0
        else 0.0
    )

    equity = [initial_capital]
    for t in trades:
        equity.append(equity[-1] + t["pnl"])
    peak = equity[0]
    max_dd = 0.0
    for val in equity:
        peak = max(peak, val)
        dd = (peak - val) / peak * 100
        max_dd = max(max_dd, dd)

    days = len(set(t.get("entry_date", "") for t in trades))
    years = max(days / 252, 0.01)
    ann_return = ((final_capital / initial_capital) ** (1 / years) - 1) * 100

    return {
        "total_return": round(total_return, 2),
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 1),
        "sharpe_ratio": round(float(sharpe), 2),
        "max_drawdown": round(max_dd, 2),
        "total_trades": len(trades),
        "annualized_return": round(ann_return, 2),
        "final_capital": round(final_capital, 2),
    }


def _run_momentum(
    symbol: str,
    dates: list[str],
    closes: list[float],
    highs: list[float],
    lows: list[float],
    args: RunMomentumBacktestArgs,
) -> list[dict]:
    """Core loop. Returns the list of closed trades."""
    trades: list[dict] = []
    capital = args.initial_capital
    lookback = args.lookback

    i = lookback
    while i < len(closes) - 1:
        momentum = ((closes[i] - closes[i - lookback]) / closes[i - lookback]) * 100
        if abs(momentum) < args.momentum_threshold:
            i += 1
            continue

        direction = "long" if momentum > 0 else "short"
        entry_price = closes[i]
        pos_size = capital * (args.position_size_pct / 100)
        units = pos_size / entry_price

        if direction == "long":
            tp_price = entry_price * (1 + args.take_profit / 100)
            sl_price = entry_price * (1 - args.stop_loss / 100)
        else:
            tp_price = entry_price * (1 - args.take_profit / 100)
            sl_price = entry_price * (1 + args.stop_loss / 100)

        hit_tp = hit_sl = False
        exit_price = closes[-1]
        exit_idx = len(closes) - 1

        for j in range(i + 1, min(i + _MAX_HOLD_BARS, len(closes))):
            if direction == "long":
                if highs[j] >= tp_price:
                    exit_price, exit_idx, hit_tp = tp_price, j, True
                    break
                if lows[j] <= sl_price:
                    exit_price, exit_idx, hit_sl = sl_price, j, True
                    break
            else:
                if lows[j] <= tp_price:
                    exit_price, exit_idx, hit_tp = tp_price, j, True
                    break
                if highs[j] >= sl_price:
                    exit_price, exit_idx, hit_sl = sl_price, j, True
                    break
        else:
            exit_idx = min(i + _MAX_HOLD_BARS, len(closes) - 1)
            exit_price = closes[exit_idx]

        if direction == "long":
            pnl = (exit_price - entry_price) * units
        else:
            pnl = (entry_price - exit_price) * units
        pnl_pct = (pnl / pos_size) * 100
        capital += pnl

        trades.append(
            {
                "entry_date": dates[i],
                "exit_date": dates[exit_idx],
                "direction": direction,
                "entry_price": round(entry_price, 5),
                "exit_price": round(exit_price, 5),
                "target_price": round(tp_price, 5),
                "stop_price": round(sl_price, 5),
                "hit_target": hit_tp,
                "hit_stop": hit_sl,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "capital_after": round(capital, 2),
                "units": round(units, 2),
                "symbol": symbol,
            }
        )
        i = exit_idx + 1

    return trades


def _result(
    args: RunMomentumBacktestArgs,
    symbol: str,
    metrics: dict[str, float | int],
    trades: list[dict],
    n_bars: int,
) -> dict[str, Any]:
    return {
        "pair": symbol,
        "strategy": "momentum",
        "params": args.model_dump(),
        "metrics": metrics,
        "trades": trades,
        "diagnostics": {
            "n_bars": n_bars,
            "n_trades": len(trades),
            "warnings": [],
            "error": None,
        },
    }


def _error_result(args: RunMomentumBacktestArgs, code: str, message: str) -> dict[str, Any]:
    return {
        "pair": args.pair,
        "strategy": "momentum",
        "params": args.model_dump(),
        "metrics": None,
        "trades": [],
        "diagnostics": {
            "n_bars": 0,
            "n_trades": 0,
            "warnings": [],
            "error": {"code": code, "message": message},
        },
    }


async def run_momentum_backtest_impl(args: RunMomentumBacktestArgs) -> dict[str, Any]:
    """Run the momentum backtest. Returns a dict, never raises."""
    settings = get_settings()
    if not settings.massive_api_key:
        return _error_result(args, "massive_unconfigured", "MASSIVE_API_KEY not set")

    client = MassiveDataClient(
        api_key=settings.massive_api_key,
        cache_dir=Path(settings.massive_cache_dir),
    )

    try:
        symbol = await client.resolve_fx_pair(args.pair)
        _, spot_date = await client.latest_close(symbol)
        start = spot_date - timedelta(days=args.history_days)
        bars = await client.fetch_ohlc_bars(symbol, start, spot_date)
    except InvalidPairError as exc:
        return _error_result(args, "invalid_pair", str(exc))
    except InsufficientDataError as exc:
        return _error_result(args, "insufficient_data", str(exc))
    except MassiveAuthError as exc:
        return _error_result(args, "massive_auth", str(exc))
    except MassiveAPIError as exc:
        return _error_result(args, "massive_api", str(exc))

    bars = bars.sort_index()
    closes = [float(c) for c in bars["close"].to_numpy()]
    highs = [float(h) for h in bars["high"].to_numpy()]
    lows = [float(low) for low in bars["low"].to_numpy()]
    dates = [pd.Timestamp(d).strftime("%Y-%m-%d") for d in bars.index]

    if len(closes) < args.lookback + 5:
        return _error_result(
            args,
            "insufficient_data",
            f"only {len(closes)} bars for {symbol}; need >= {args.lookback + 5} "
            f"for lookback {args.lookback}",
        )

    trades = _run_momentum(symbol, dates, closes, highs, lows, args)
    metrics = _calculate_metrics(trades, args.initial_capital)
    return _result(args, symbol, metrics, trades, n_bars=len(closes))
