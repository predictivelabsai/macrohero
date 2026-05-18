"""One-off script: generate golden output fixtures by running the OLD api/
code (api/src/macrohero/fx/tool.py) against the existing Massive parquet cache.

Run this once during Phase 1. The output JSON files are committed and become
the regression baseline for the new numerics service and the future TS tool
wrapper.

Usage:
    cd /Users/elaine/Documents/macrohero
    MASSIVE_API_KEY=$YOUR_KEY uv --directory api run python ../apps/numerics/scripts/generate_golden_fixtures.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# Resolve the api/ src dir so we can import the OLD code.
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_REPO_ROOT / "api" / "src"))

from macrohero.fx.tool import (  # type: ignore  # noqa: E402
    FactorShock,
    RunFactorProjectionArgs,
    run_factor_projection_impl,
)


_OUTPUT_DIR = (
    Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "golden"
)


# 20 scenarios covering: a range of pairs, horizons, factor counts, severity
# tiers, directions, and error envelopes. Each tuple is (scenario_id, args).
SCENARIOS: list[tuple[str, RunFactorProjectionArgs]] = [
    # Single-factor scenarios across severities
    (
        "scenario_01",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            factors=[FactorShock(name="Brent crude", direction="down", severity="mild")],
        ),
    ),
    (
        "scenario_02",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            factors=[FactorShock(name="Brent crude", direction="down", severity="moderate")],
        ),
    ),
    (
        "scenario_03",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            factors=[FactorShock(name="Brent crude", direction="down", severity="severe")],
        ),
    ),
    (
        "scenario_04",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            factors=[FactorShock(name="Brent crude", direction="down", severity="extreme")],
        ),
    ),
    # Direction flips
    (
        "scenario_05",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            factors=[FactorShock(name="WTI crude", direction="up", severity="moderate")],
        ),
    ),
    (
        "scenario_06",
        RunFactorProjectionArgs(
            pair="USD/JPY",
            horizon_days=14,
            factors=[FactorShock(name="WTI crude", direction="down", severity="moderate")],
        ),
    ),
    # Horizon sweep
    ("scenario_07", RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=1,
        factors=[FactorShock(name="S&P 500", direction="down", severity="severe")],
    )),
    ("scenario_08", RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=7,
        factors=[FactorShock(name="S&P 500", direction="down", severity="severe")],
    )),
    ("scenario_09", RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=30,
        factors=[FactorShock(name="S&P 500", direction="down", severity="severe")],
    )),
    ("scenario_10", RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=60,
        factors=[FactorShock(name="S&P 500", direction="down", severity="severe")],
    )),
    ("scenario_11", RunFactorProjectionArgs(
        pair="EUR/USD",
        horizon_days=90,
        factors=[FactorShock(name="S&P 500", direction="down", severity="severe")],
    )),
    # Multi-pair sweep
    (
        "scenario_12",
        RunFactorProjectionArgs(
            pair="GBP/USD",
            horizon_days=30,
            factors=[FactorShock(name="S&P 500", direction="up", severity="moderate")],
        ),
    ),
    (
        "scenario_13",
        RunFactorProjectionArgs(
            pair="AUD/USD",
            horizon_days=30,
            factors=[FactorShock(name="WTI crude", direction="up", severity="moderate")],
        ),
    ),
    (
        "scenario_14",
        RunFactorProjectionArgs(
            pair="USD/CHF",
            horizon_days=30,
            factors=[FactorShock(name="VIX (volatility)", direction="up", severity="severe")],
        ),
    ),
    (
        "scenario_15",
        RunFactorProjectionArgs(
            pair="USD/CAD",
            horizon_days=30,
            factors=[FactorShock(name="WTI crude", direction="down", severity="severe")],
        ),
    ),
    # Multi-factor scenarios
    (
        "scenario_16",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=30,
            factors=[
                FactorShock(name="S&P 500", direction="down", severity="severe"),
                FactorShock(name="VIX (volatility)", direction="up", severity="severe"),
            ],
        ),
    ),
    (
        "scenario_17",
        RunFactorProjectionArgs(
            pair="USD/JPY",
            horizon_days=30,
            factors=[
                # US 20+Y Treasury ETF acts as the long-yield proxy in FACTOR_UNIVERSE
                # (price moves inversely to yield, so "down" here = "yields rise").
                FactorShock(name="US 20+Y Treasury", direction="down", severity="severe"),
                FactorShock(name="Dollar Index", direction="up", severity="moderate"),
                FactorShock(name="S&P 500", direction="up", severity="mild"),
            ],
        ),
    ),
    (
        "scenario_18",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            factors=[
                FactorShock(name="WTI crude", direction="down", severity="severe"),
                FactorShock(name="Brent crude", direction="down", severity="severe"),
                FactorShock(name="Energy sector", direction="down", severity="severe"),
                FactorShock(name="High-yield credit", direction="down", severity="moderate"),
            ],
        ),
    ),
    # Custom regression window
    (
        "scenario_19",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            regression_window_days=60,
            factors=[FactorShock(name="Brent crude", direction="down", severity="severe")],
        ),
    ),
    (
        "scenario_20",
        RunFactorProjectionArgs(
            pair="EUR/USD",
            horizon_days=14,
            regression_window_days=500,
            factors=[FactorShock(name="Brent crude", direction="down", severity="severe")],
        ),
    ),
]


async def main() -> int:
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    failed = 0
    for sid, args in SCENARIOS:
        try:
            result = await run_factor_projection_impl(args)
        except Exception as exc:  # pragma: no cover
            print(f"[FAIL] {sid}: {exc!r}")
            failed += 1
            continue

        out_path = _OUTPUT_DIR / f"{sid}.json"
        envelope = {
            "scenario_id": sid,
            "input": args.model_dump(),
            "output": result,
        }
        out_path.write_text(json.dumps(envelope, indent=2, sort_keys=True) + "\n")
        print(f"[OK]   {sid} -> {out_path.relative_to(_REPO_ROOT)}")
        written += 1

    print(f"\nWrote {written} fixtures; {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
