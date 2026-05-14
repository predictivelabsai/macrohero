from datetime import date
from pathlib import Path

import pytest
from massive.exceptions import BadResponse
from massive.rest.models.aggs import Agg
from massive.rest.models.tickers import Ticker

from macrohero.fx.data import InvalidPairError, MassiveAuthError, MassiveDataClient

# ---------------------------------------------------------------------------
# Helpers to build SDK model objects without going through from_dict
# ---------------------------------------------------------------------------

def _make_agg(close: float, timestamp: int) -> Agg:
    a = Agg()
    a.close = close
    a.timestamp = timestamp
    return a


def _make_ticker(ticker_sym: str) -> Ticker:
    t = Ticker()
    t.ticker = ticker_sym
    t.active = True
    return t


def _bad_response(status: int) -> BadResponse:
    exc = BadResponse(f"HTTP {status}")
    exc.http_status = status  # type: ignore[attr-defined]
    return exc


# ---------------------------------------------------------------------------
# resolve_fx_pair tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_resolve_fx_pair_variants(tmp_path: Path, monkeypatch) -> None:
    def fake_list_tickers(self, ticker=None, market=None, active=None, **kwargs):
        return iter([_make_ticker("C:EURUSD")])

    monkeypatch.setattr("massive.RESTClient.list_tickers", fake_list_tickers)

    client = MassiveDataClient(api_key="test_key", cache_dir=tmp_path)
    assert await client.resolve_fx_pair("EUR/USD") == "C:EURUSD"
    assert await client.resolve_fx_pair("eurusd") == "C:EURUSD"
    assert await client.resolve_fx_pair("EURUSD") == "C:EURUSD"
    assert await client.resolve_fx_pair("C:EURUSD") == "C:EURUSD"


@pytest.mark.asyncio
async def test_resolve_fx_pair_unknown_raises(tmp_path: Path, monkeypatch) -> None:
    def fake_list_tickers(self, ticker=None, market=None, active=None, **kwargs):
        return iter([])

    monkeypatch.setattr("massive.RESTClient.list_tickers", fake_list_tickers)

    client = MassiveDataClient(api_key="test_key", cache_dir=tmp_path)
    with pytest.raises(InvalidPairError):
        await client.resolve_fx_pair("XXX/YYY")


@pytest.mark.asyncio
async def test_latest_close_returns_most_recent_bar(tmp_path: Path, monkeypatch) -> None:
    def fake_list_aggs(self, ticker, multiplier, timespan, from_, to, **kwargs):
        return iter([
            _make_agg(1.10, 1704067200000),
            _make_agg(1.11, 1704153600000),
            _make_agg(1.12, 1704240000000),
        ])

    monkeypatch.setattr("massive.RESTClient.list_aggs", fake_list_aggs)

    client = MassiveDataClient(api_key="test_key", cache_dir=tmp_path)
    close, when = await client.latest_close("C:EURUSD")
    assert close == pytest.approx(1.12)
    assert when == date(2024, 1, 3)


@pytest.mark.asyncio
async def test_resolve_fx_pair_401_raises_auth_error(tmp_path: Path, monkeypatch) -> None:
    def fake_list_tickers(self, ticker=None, market=None, active=None, **kwargs):
        raise _bad_response(401)

    monkeypatch.setattr("massive.RESTClient.list_tickers", fake_list_tickers)

    client = MassiveDataClient(api_key="bad", cache_dir=tmp_path)
    with pytest.raises(MassiveAuthError):
        await client.resolve_fx_pair("EUR/USD")
