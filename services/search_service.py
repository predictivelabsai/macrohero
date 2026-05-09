import asyncio
import logging
import os
from utils.config import load_config

logger = logging.getLogger(__name__)

_tavily_client = None


def _get_tavily():
    global _tavily_client
    if _tavily_client is None:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return None
        from tavily import TavilyClient
        _tavily_client = TavilyClient(api_key=api_key)
    return _tavily_client


async def search_tavily(query: str, max_results: int = 5) -> list[dict]:
    client = _get_tavily()
    if client is None:
        return []
    config = load_config()
    tavily_cfg = config.get("search", {}).get("tavily", {})
    try:
        result = await asyncio.to_thread(
            client.search,
            query=query,
            search_depth=tavily_cfg.get("search_depth", "advanced"),
            topic=tavily_cfg.get("topic", "news"),
            max_results=max_results,
        )
        articles = []
        for r in result.get("results", []):
            articles.append({
                "url": r.get("url", ""),
                "title": r.get("title", ""),
                "summary": r.get("content", "")[:500],
                "source": r.get("url", "").split("/")[2] if "/" in r.get("url", "") else "",
            })
        return articles
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        return []


async def discover_macro_news(categories: list[str], max_per_category: int = 3) -> list[dict]:
    all_results = []
    for cat_name in categories[:3]:
        results = await search_tavily(f"latest {cat_name} macro economic news today", max_per_category)
        all_results.extend(results)
    return all_results
