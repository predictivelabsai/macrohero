import asyncio
import logging
from datetime import datetime, timezone
import feedparser
from db.pool import fetch_one

logger = logging.getLogger(__name__)


def _parse_date(entry) -> datetime | None:
    for field in ("published_parsed", "updated_parsed"):
        val = getattr(entry, field, None) or entry.get(field)
        if val:
            try:
                from time import mktime
                return datetime.fromtimestamp(mktime(val), tz=timezone.utc)
            except Exception:
                pass
    return None


async def fetch_rss_feed(source: dict) -> list[dict]:
    rss_url = source.get("rss_url")
    if not rss_url:
        return []

    try:
        feed = await asyncio.to_thread(feedparser.parse, rss_url)
    except Exception as e:
        logger.error(f"Failed to parse RSS from {source['name']}: {e}")
        return []

    articles = []
    for entry in feed.entries:
        url = entry.get("link", "").strip()
        if not url:
            continue

        existing = await asyncio.to_thread(
            fetch_one, "SELECT id FROM macro_news WHERE url = :url", {"url": url}
        )
        if existing:
            continue

        articles.append({
            "url": url,
            "title": entry.get("title", "Untitled").strip(),
            "summary": entry.get("summary", "")[:1000].strip(),
            "author": entry.get("author", "").strip(),
            "published_at": _parse_date(entry),
            "language": source.get("language", "en"),
            "source_domain": source["domain"],
        })

    logger.info(f"RSS {source['name']}: {len(articles)} new articles from {len(feed.entries)} entries")
    return articles


async def fetch_all_rss(sources: list[dict]) -> list[dict]:
    tasks = [fetch_rss_feed(src) for src in sources]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    all_articles = []
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"RSS fetch error: {result}")
            continue
        all_articles.extend(result)
    return all_articles
