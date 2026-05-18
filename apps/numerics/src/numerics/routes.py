"""HTTP routes for the numerics service.

Internal service: no auth, no CORS, no rate limiting. Exposes three endpoints
that the TS apps/api consumes:

- POST /v1/projection — run the deterministic FX projection.
- GET  /v1/factors    — return the factor universe (used by codegen).
- GET  /healthz       — liveness check for docker-compose.
"""

from __future__ import annotations

import dataclasses
from typing import Any

from fastapi import APIRouter

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
