"""HTTP routes for the numerics service.

Internal service: no auth, no CORS, no rate limiting. Exposes endpoints that
the TS apps/api (and other internal verticals, e.g. AssetHero) consume:

- POST /v1/projection        — run the deterministic FX projection.
- POST /v1/backtest/momentum — run a momentum FX backtest.
- GET  /v1/factors           — return the factor universe (used by codegen).
- GET  /healthz              — liveness check for docker-compose.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from fastapi import APIRouter

from numerics.backtest_service import (
    RunMomentumBacktestArgs,
    run_momentum_backtest_impl,
)
from numerics.factors import FACTOR_UNIVERSE
from numerics.projection_service import (
    RunFactorProjectionArgs,
    run_factor_projection_impl,
)

router = APIRouter()


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/factors")
async def list_factors() -> dict[str, list[dict[str, Any]]]:
    """Return the factor universe.

    Consumed by `pnpm gen:factors` in the TS workspace to emit a typed enum.
    Field shape matches the FactorSpec dataclass.
    """
    return {"factors": [dataclasses.asdict(f) for f in FACTOR_UNIVERSE]}


@router.post("/v1/projection")
async def run_projection(args: RunFactorProjectionArgs) -> dict[str, Any]:
    """Run the deterministic FX factor projection.

    Returns the same dict shape as today's `run_factor_projection_impl(...)`.
    Domain-level errors (invalid pair, insufficient data, etc.) come back in
    the body's `diagnostics.error` envelope with HTTP 200 — matching how the
    LangChain tool wrapper presents them. Pydantic validation failures still
    return 422.
    """
    return await run_factor_projection_impl(args)


@router.post("/v1/backtest/momentum")
async def run_backtest_momentum(args: RunMomentumBacktestArgs) -> dict[str, Any]:
    """Run a momentum FX backtest over Massive daily bars.

    Domain-level problems (unconfigured key, invalid pair, insufficient data)
    come back in the body's `diagnostics.error` envelope with HTTP 200, the
    same convention as `/v1/projection`. Pydantic validation failures return
    422. On success, `metrics` and `trades` are populated and
    `diagnostics.error` is null.
    """
    return await run_momentum_backtest_impl(args)
