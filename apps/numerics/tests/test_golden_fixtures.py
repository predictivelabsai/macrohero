"""Regression test: the new numerics service must produce byte-identical JSON
to the OLD api/'s run_factor_projection_impl for each golden fixture."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from numerics.projection_service import (
    RunFactorProjectionArgs,
    run_factor_projection_impl,
)

_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "golden"

# These scenarios depend on live Massive data. Skip if no API key, but provide
# a clear marker so the user knows the regression isn't being checked.
_MASSIVE_KEY = os.environ.get("MASSIVE_API_KEY")


def _load_fixtures() -> list[tuple[str, dict]]:
    fixtures: list[tuple[str, dict]] = []
    for path in sorted(_FIXTURES_DIR.glob("scenario_*.json")):
        envelope = json.loads(path.read_text())
        fixtures.append((envelope["scenario_id"], envelope))
    return fixtures


@pytest.mark.skipif(not _MASSIVE_KEY, reason="MASSIVE_API_KEY not set; can't reach live data")
@pytest.mark.parametrize("scenario_id, envelope", _load_fixtures(), ids=lambda v: v if isinstance(v, str) else "")
@pytest.mark.asyncio
async def test_golden_fixture(scenario_id: str, envelope: dict, monkeypatch) -> None:
    # Use the same MASSIVE_CACHE_DIR as the api/ that generated the fixtures.
    # The parquet cache lives at api/.cache/massive/ — point at it explicitly
    # so we hit the same cached responses.
    cache_dir = Path(__file__).parent.parent.parent.parent / "api" / ".cache" / "massive"
    monkeypatch.setenv("MASSIVE_CACHE_DIR", str(cache_dir))
    monkeypatch.setenv("MASSIVE_API_KEY", _MASSIVE_KEY or "test_key")

    from numerics.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    args = RunFactorProjectionArgs(**envelope["input"])
    actual = await run_factor_projection_impl(args)
    expected = envelope["output"]

    # Compare JSON-normalized to catch any field-order or float-format drift.
    actual_json = json.dumps(actual, indent=2, sort_keys=True)
    expected_json = json.dumps(expected, indent=2, sort_keys=True)
    assert actual_json == expected_json, (
        f"{scenario_id} drifted from golden baseline. "
        "If this is intentional (math/algorithm change), regenerate the fixture by re-running "
        "apps/numerics/scripts/generate_golden_fixtures.py."
    )
