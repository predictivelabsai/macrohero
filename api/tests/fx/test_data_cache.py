from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from massive.exceptions import BadResponse
from massive.rest.models.aggs import Agg

from macrohero.fx.data import (
    InsufficientDataError,
    InvalidPairError,
    MassiveAPIError,
    MassiveAuthError,
    MassiveDataClient,
    _cache_path_for,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_agg(close: float, timestamp: int) -> Agg:
    a = Agg()
    a.close = close
    a.timestamp = timestamp
    return a


def _bad_response(status: int) -> BadResponse:
    exc = BadResponse(f"HTTP {status}")
    exc.http_status = status  # type: ignore[attr-defined]
    return exc


# ---------------------------------------------------------------------------
# Cache path helper (pure, no mock needed)
# ---------------------------------------------------------------------------

def test_cache_path_includes_symbol_and_dates(tmp_path: Path) -> None:
    p = _cache_path_for(tmp_path, "C:EURUSD", date(2024, 1, 1), date(2024, 6, 1))
    assert p.parent.parent == tmp_path
    assert "2024-01-01" in p.name
    assert "2024-06-01" in p.name
    assert p.suffix == ".parquet"
    # Forbid ':' in directory names so Windows / S3 are happy later
    assert ":" not in str(p)


# ---------------------------------------------------------------------------
# fetch_bars tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_bars_writes_then_reads_cache(tmp_path: Path, monkeypatch) -> None:
    call_count = {"n": 0}

    def fake_list_aggs(self, ticker, multiplier, timespan, from_, to, **kwargs):
        call_count["n"] += 1
        return iter([
            _make_agg(1.10, 1704067200000),
            _make_agg(1.11, 1704153600000),
        ])

    monkeypatch.setattr("massive.RESTClient.list_aggs", fake_list_aggs)

    client = MassiveDataClient(api_key="test_key", cache_dir=tmp_path)
    df = await client.fetch_bars("C:EURUSD", date(2024, 1, 1), date(2024, 1, 2))
    assert list(df.columns) == ["close"]
    assert len(df) == 2

    # Second call must hit the cache; no second SDK request.
    df2 = await client.fetch_bars("C:EURUSD", date(2024, 1, 1), date(2024, 1, 2))
    pd.testing.assert_frame_equal(df, df2)
    assert call_count["n"] == 1


@pytest.mark.asyncio
async def test_fetch_bars_404_pair_raises_invalid_pair(tmp_path: Path, monkeypatch) -> None:
    def fake_list_aggs(self, ticker, multiplier, timespan, from_, to, **kwargs):
        raise _bad_response(404)

    monkeypatch.setattr("massive.RESTClient.list_aggs", fake_list_aggs)

    client = MassiveDataClient(api_key="test_key", cache_dir=tmp_path)
    with pytest.raises(InvalidPairError):
        await client.fetch_bars("C:BADPAIR", date(2024, 1, 1), date(2024, 1, 2))


@pytest.mark.asyncio
async def test_fetch_bars_401_raises_auth_error(tmp_path: Path, monkeypatch) -> None:
    def fake_list_aggs(self, ticker, multiplier, timespan, from_, to, **kwargs):
        raise _bad_response(401)

    monkeypatch.setattr("massive.RESTClient.list_aggs", fake_list_aggs)

    client = MassiveDataClient(api_key="bad", cache_dir=tmp_path)
    with pytest.raises(MassiveAuthError):
        await client.fetch_bars("C:EURUSD", date(2024, 1, 1), date(2024, 1, 2))


@pytest.mark.asyncio
async def test_fetch_bars_5xx_retries_then_raises_api_error(tmp_path: Path, monkeypatch) -> None:
    def fake_list_aggs(self, ticker, multiplier, timespan, from_, to, **kwargs):
        raise _bad_response(503)

    monkeypatch.setattr("massive.RESTClient.list_aggs", fake_list_aggs)

    client = MassiveDataClient(api_key="test_key", cache_dir=tmp_path)
    with pytest.raises(MassiveAPIError):
        await client.fetch_bars("C:EURUSD", date(2024, 1, 1), date(2024, 1, 2))


@pytest.mark.asyncio
async def test_fetch_bars_empty_results_raises_insufficient_data(
    tmp_path: Path, monkeypatch
) -> None:
    def fake_list_aggs(self, ticker, multiplier, timespan, from_, to, **kwargs):
        return iter([])

    monkeypatch.setattr("massive.RESTClient.list_aggs", fake_list_aggs)

    client = MassiveDataClient(api_key="test_key", cache_dir=tmp_path)
    with pytest.raises(InsufficientDataError):
        await client.fetch_bars("C:EURUSD", date(2024, 1, 1), date(2024, 1, 2))
