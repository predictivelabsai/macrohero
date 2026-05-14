"""Tests for the Tavily-backed search_current_events tool."""

from typing import Any

import httpx
import pytest

from macrohero.chat.search import (
    SearchCurrentEventsArgs,
    search_current_events_impl,
)


def test_args_validate_query_length() -> None:
    with pytest.raises(ValueError):
        SearchCurrentEventsArgs(query="hi")  # < 3 chars
    with pytest.raises(ValueError):
        SearchCurrentEventsArgs(query="x" * 201)


def test_args_validate_max_results_bounds() -> None:
    with pytest.raises(ValueError):
        SearchCurrentEventsArgs(query="test query", max_results=0)
    with pytest.raises(ValueError):
        SearchCurrentEventsArgs(query="test query", max_results=11)


@pytest.mark.asyncio
async def test_search_returns_error_when_key_missing(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "")
    # Ensure get_settings sees the cleared key.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.test")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.test/.well-known/jwks.json")
    from macrohero.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    out = await search_current_events_impl(query="Hormuz war", max_results=3)
    assert out["error"] is not None
    assert out["results"] == []
    assert "TAVILY_API_KEY" in out["error"]


@pytest.mark.asyncio
async def test_search_parses_tavily_response(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test_key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.test")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.test/.well-known/jwks.json")
    from macrohero.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    fake_response = {
        "answer": "Recent tensions in the Hormuz strait...",
        "results": [
            {
                "title": "Strait of Hormuz tensions escalate",
                "url": "https://example.com/news/1",
                "content": "Iran has reportedly...",
                "score": 0.95,
            },
            {
                "title": "Oil prices spike on Hormuz fears",
                "url": "https://example.com/news/2",
                "content": "Brent crude climbed...",
                "score": 0.88,
            },
        ],
    }

    class _MockResponse:
        status_code = 200

        def json(self) -> dict[str, Any]:
            return fake_response

    class _MockClient:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self) -> "_MockClient":
            return self

        async def __aexit__(self, *_args) -> None:
            pass

        async def post(self, *_args, **_kwargs) -> _MockResponse:
            return _MockResponse()

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)

    out = await search_current_events_impl(query="Hormuz war", max_results=5)
    assert out["error"] is None
    assert out["answer"] == "Recent tensions in the Hormuz strait..."
    assert len(out["results"]) == 2
    assert out["results"][0]["title"] == "Strait of Hormuz tensions escalate"
    assert out["results"][0]["url"] == "https://example.com/news/1"
    # Score is dropped from the public shape (we only forward title/url/content).
    assert "score" not in out["results"][0]


@pytest.mark.asyncio
async def test_search_handles_http_error(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test_key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.test")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.test/.well-known/jwks.json")
    from macrohero.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    class _RaisingClient:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self) -> "_RaisingClient":
            return self

        async def __aexit__(self, *_args) -> None:
            pass

        async def post(self, *_args, **_kwargs) -> None:
            raise httpx.ConnectError("network down")

    monkeypatch.setattr(httpx, "AsyncClient", _RaisingClient)

    out = await search_current_events_impl(query="Hormuz war", max_results=5)
    assert out["error"] is not None
    assert out["results"] == []
    assert "network down" in out["error"]


@pytest.mark.asyncio
async def test_search_handles_non_200_status(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_API_KEY", "test_key")
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost/db")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.test")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://example.test/.well-known/jwks.json")
    from macrohero.config import get_settings

    get_settings.cache_clear()  # type: ignore[attr-defined]

    class _BadResponse:
        status_code = 429

        def json(self) -> dict[str, Any]:
            return {}

    class _MockClient:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self) -> "_MockClient":
            return self

        async def __aexit__(self, *_args) -> None:
            pass

        async def post(self, *_args, **_kwargs) -> _BadResponse:
            return _BadResponse()

    monkeypatch.setattr(httpx, "AsyncClient", _MockClient)

    out = await search_current_events_impl(query="Hormuz war", max_results=5)
    assert out["error"] is not None
    assert "429" in out["error"]
    assert out["results"] == []
