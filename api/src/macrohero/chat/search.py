"""Tavily-backed web search tool for the chat agent.

Exposes a single LangChain @tool the LLM can call when it needs current-event
context (recent news, named entities, geopolitical situations) that aren't in
its training data. The tool never raises into the streaming loop: missing key
or HTTP errors surface as a structured `{error, results: []}` payload.
"""

from __future__ import annotations

from typing import Any

import httpx
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from macrohero.config import get_settings

_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_REQUEST_TIMEOUT_S = 20.0


class SearchCurrentEventsArgs(BaseModel):
    query: str = Field(
        min_length=3,
        max_length=200,
        description="Search query. Be specific: include the event name and any timeframe.",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Number of search snippets to return.",
    )


async def search_current_events_impl(query: str, max_results: int) -> dict[str, Any]:
    """Direct HTTP call to Tavily; returns a structured dict, never raises."""
    settings = get_settings()
    if not settings.tavily_api_key:
        return {
            "query": query,
            "answer": None,
            "results": [],
            "error": "TAVILY_API_KEY not configured.",
        }

    payload = {
        "api_key": settings.tavily_api_key,
        "query": query,
        "max_results": max_results,
        "search_depth": "basic",
        "include_answer": True,
        "topic": "general",
    }

    try:
        async with httpx.AsyncClient(timeout=_REQUEST_TIMEOUT_S) as client:
            resp = await client.post(_TAVILY_ENDPOINT, json=payload)
    except httpx.HTTPError as exc:
        return {
            "query": query,
            "answer": None,
            "results": [],
            "error": f"Search request failed: {exc!s}"[:200],
        }

    if resp.status_code != 200:
        return {
            "query": query,
            "answer": None,
            "results": [],
            "error": f"Search returned HTTP {resp.status_code}.",
        }

    data = resp.json()
    return {
        "query": query,
        "answer": data.get("answer"),
        "results": [
            {
                "title": r.get("title", ""),
                "url": r.get("url", ""),
                "content": r.get("content", "")[:600],
            }
            for r in data.get("results", [])
        ],
        "error": None,
    }


@tool(args_schema=SearchCurrentEventsArgs)
async def search_current_events(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web for current events, recent news, or named entities you
    don't have detailed knowledge of.

    Use this BEFORE calling `run_factor_projection` whenever the user mentions
    a specific recent event, ongoing crisis, person, place, or named scenario
    you can't confidently identify on your own — for example "the Hormuz war",
    "the latest CPI print", or "yesterday's ECB decision". Then synthesize the
    search snippets into the factor-shock reasoning that precedes the
    projection call.

    Returns: {query, answer, results: [{title, url, content}], error}.
    """
    return await search_current_events_impl(query=query, max_results=max_results)
