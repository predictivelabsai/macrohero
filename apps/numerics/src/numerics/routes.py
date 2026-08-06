"""HTTP routes for the numerics service.

Exposes endpoints that the TS apps/api and other internal verticals (e.g.
AssetHero) consume:

- GET  /healthz              — liveness check for docker-compose (always open).
- GET  /v1/catalog           — strategies, supported pairs, and param ranges.
- GET  /v1/factors           — return the factor universe (used by codegen).
- POST /v1/projection        — run the deterministic FX projection.
- POST /v1/backtest/momentum — run a momentum FX backtest.

Auth: the service is optionally gated by a shared secret. If env
`NUMERICS_SERVICE_KEY` is set, every `/v1/*` request must send header
`X-Service-Key: <value>` (401 on mismatch). If unset, all callers are allowed
so local dev and existing internal callers keep working. `/healthz` is never
gated.

Convention: domain-level problems (invalid pair, insufficient data, unconfigured
key, etc.) come back in the body's `diagnostics.error` envelope with HTTP 200,
matching the LangChain tool wrapper. Pydantic validation failures return 422.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException

from numerics.backtest_service import (
    RunMomentumBacktestArgs,
    build_catalog,
    run_momentum_backtest_impl,
)
from numerics.config import get_settings
from numerics.factors import FACTOR_UNIVERSE
from numerics.projection_service import (
    RunFactorProjectionArgs,
    run_factor_projection_impl,
)

logger = logging.getLogger("numerics.access")


def _attach_requested_by(
    result: dict[str, Any], user_id: str | None, source: str | None
) -> dict[str, Any]:
    """Echo the calling user into diagnostics for traceability. Stateless — no
    persistence; this is correlation metadata only.

    Absent headers leave the response untouched. Only the correlation ids
    (never secrets) are logged.
    """
    if user_id is None and source is None:
        return result

    diagnostics = result.get("diagnostics")
    if isinstance(diagnostics, dict):
        diagnostics["requested_by"] = {"user_id": user_id, "source": source}

    logger.info(
        "numerics request user_id=%s source=%s strategy=%s",
        user_id,
        source,
        result.get("strategy"),
    )
    return result


async def require_service_key(x_service_key: str | None = Header(default=None)) -> None:
    """Gate /v1/* with a shared secret when NUMERICS_SERVICE_KEY is configured.

    No-op when the env var is unset (local dev / existing internal callers).
    Never reveals the expected value.
    """
    expected = get_settings().numerics_service_key
    if expected and x_service_key != expected:
        raise HTTPException(status_code=401, detail="invalid or missing X-Service-Key")


router = APIRouter()

# All /v1 routes share the optional service-key gate.
v1 = APIRouter(prefix="/v1", dependencies=[Depends(require_service_key)])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@v1.get("/catalog")
async def catalog() -> dict[str, Any]:
    """Discovery payload so consumers build their UI without hardcoding.

    Returns the available strategies, supported FX pairs, and the numeric
    parameter ranges (min/max/default) derived from the backtest request
    model's own Field constraints.
    """
    return build_catalog()


@v1.get("/factors")
async def list_factors() -> dict[str, list[dict[str, Any]]]:
    """Return the factor universe.

    Consumed by `pnpm gen:factors` in the TS workspace to emit a typed enum.
    Field shape matches the FactorSpec dataclass.
    """
    return {"factors": [dataclasses.asdict(f) for f in FACTOR_UNIVERSE]}


@v1.post("/projection")
async def run_projection(
    args: RunFactorProjectionArgs,
    x_user_id: str | None = Header(default=None),
    x_user_source: str | None = Header(default=None),
) -> dict[str, Any]:
    """Run the deterministic FX factor projection.

    Returns the same dict shape as today's `run_factor_projection_impl(...)`.
    Domain-level errors (invalid pair, insufficient data, etc.) come back in
    the body's `diagnostics.error` envelope with HTTP 200 — matching how the
    LangChain tool wrapper presents them. Pydantic validation failures still
    return 422.

    Optional `X-User-Id` / `X-User-Source` headers are echoed into
    `diagnostics.requested_by` for traceability. They are never persisted.
    """
    result = await run_factor_projection_impl(args)
    return _attach_requested_by(result, x_user_id, x_user_source)


@v1.post("/backtest/momentum")
async def run_backtest_momentum(
    args: RunMomentumBacktestArgs,
    x_user_id: str | None = Header(default=None),
    x_user_source: str | None = Header(default=None),
) -> dict[str, Any]:
    """Run a momentum FX backtest over Massive daily bars.

    Domain-level problems (unconfigured key, invalid pair, insufficient data)
    come back in the body's `diagnostics.error` envelope with HTTP 200, the
    same convention as `/v1/projection`. Pydantic validation failures return
    422. On success, `metrics` and `trades` are populated and
    `diagnostics.error` is null.

    Optional `X-User-Id` / `X-User-Source` headers are echoed into
    `diagnostics.requested_by` for traceability. They are never persisted —
    AssetHero owns FX run history; numerics stays stateless.
    """
    result = await run_momentum_backtest_impl(args)
    return _attach_requested_by(result, x_user_id, x_user_source)


router.include_router(v1)
