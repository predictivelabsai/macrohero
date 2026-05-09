import asyncio
import logging
from db.pool import fetch_one, execute_sql
from services.news_service import fetch_all_rss
from services.scraper_service import scrape_article
from services.classify_service import classify_article, save_news_categories
from utils.config import get_all_sources

logger = logging.getLogger(__name__)


async def _process_article(raw: dict, article_queue: asyncio.Queue, category_queues: dict):
    source = await asyncio.to_thread(
        fetch_one,
        "SELECT id FROM sources WHERE domain = :domain",
        {"domain": raw["source_domain"]},
    )
    source_id = source["id"] if source else None

    result = await asyncio.to_thread(fetch_one, """
        INSERT INTO macro_news (source_id, url, title, summary, author, published_at, language)
        VALUES (:source_id, :url, :title, :summary, :author, :published_at, :language)
        ON CONFLICT (url) DO NOTHING
        RETURNING id
    """, {
        "source_id": source_id,
        "url": raw["url"],
        "title": raw["title"],
        "summary": raw.get("summary", ""),
        "author": raw.get("author", ""),
        "published_at": raw.get("published_at"),
        "language": raw.get("language", "en"),
    })

    if not result:
        return

    article_id = str(result["id"])

    scraped = await scrape_article(raw["url"])
    if scraped.get("full_text"):
        await asyncio.to_thread(execute_sql, """
            UPDATE macro_news SET full_text = :text, word_count = :wc
            WHERE id = :id
        """, {"text": scraped["full_text"], "wc": scraped["word_count"], "id": article_id})

    author = raw.get("author") or scraped.get("author", "")
    if author and not raw.get("author"):
        await asyncio.to_thread(execute_sql, "UPDATE macro_news SET author = :author WHERE id = :id",
                     {"author": author, "id": article_id})

    categories = await asyncio.to_thread(classify_article, raw["title"], raw.get("summary", ""), scraped.get("full_text", ""))
    await asyncio.to_thread(save_news_categories, article_id, categories)

    article_for_push = await asyncio.to_thread(_build_push_article, article_id)
    if article_for_push:
        try:
            article_queue.put_nowait(article_for_push)
        except asyncio.QueueFull:
            pass
        for cat in categories:
            q = category_queues.get(cat["slug"])
            if q:
                try:
                    q.put_nowait(article_for_push)
                except asyncio.QueueFull:
                    pass


def _build_push_article(article_id: str) -> dict | None:
    return fetch_one("""
        SELECT n.id, n.title, n.url, n.author, n.published_at,
               n.region, n.currency_tag, n.event_category,
               n.predicted_direction, n.predicted_magnitude, n.market_reasoning,
               s.name AS source_name
        FROM macro_news n
        LEFT JOIN sources s ON s.id = n.source_id
        WHERE n.id = :id
    """, {"id": article_id})


async def run_feed_scheduler(
    config: dict,
    shutdown_event,
    article_queue: asyncio.Queue,
    category_queues: dict,
):
    interval = config["app"].get("fetch_interval_seconds", 300)
    logger.info(f"Feed scheduler started (interval={interval}s)")

    await asyncio.sleep(5)

    cycle = 0
    while not shutdown_event.is_set():
        cycle += 1
        logger.info(f"Feed scheduler cycle {cycle} starting...")
        try:
            sources = get_all_sources()
            new_articles = await fetch_all_rss(sources)
            logger.info(f"Cycle {cycle}: {len(new_articles)} new articles from RSS")

            for raw in new_articles:
                if shutdown_event.is_set():
                    break
                try:
                    await _process_article(raw, article_queue, category_queues)
                except Exception as e:
                    logger.error(f"Failed to process article {raw.get('url')}: {e}")

            if cycle % 3 == 0:
                try:
                    from services.search_service import discover_macro_news
                    from services.classify_service import get_trending_categories
                    trending = await asyncio.to_thread(get_trending_categories, 24)
                    cat_names = [c["name"] for c in trending[:3]]
                    if cat_names:
                        discovered = await discover_macro_news(cat_names)
                        for d in discovered:
                            raw_article = {
                                "url": d["url"],
                                "title": d["title"],
                                "summary": d.get("summary", ""),
                                "author": "",
                                "published_at": None,
                                "language": "en",
                                "source_domain": d.get("source", "tavily"),
                            }
                            try:
                                await _process_article(raw_article, article_queue, category_queues)
                            except Exception as e:
                                logger.error(f"Tavily article process error: {e}")
                except Exception as e:
                    logger.error(f"Tavily discovery error: {e}")

        except Exception as e:
            logger.error(f"Feed scheduler cycle {cycle} error: {e}")

        logger.info(f"Feed scheduler cycle {cycle} complete. Sleeping {interval}s...")
        try:
            await asyncio.wait_for(asyncio.shield(shutdown_event.wait()), timeout=interval)
            break
        except asyncio.TimeoutError:
            pass
