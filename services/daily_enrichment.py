import asyncio
import logging

from db.pool import fetch_all
from utils.config import load_config

logger = logging.getLogger(__name__)


async def _batch_enrichment(limit: int):
    from services.enrich_service import enrich_article
    rows = fetch_all("""
        SELECT n.id, n.title, COALESCE(n.full_text, n.summary, '') AS text,
               s.name AS source_name
        FROM macro_news n
        LEFT JOIN sources s ON s.id = n.source_id
        WHERE n.enriched_at IS NULL
          AND n.created_at > NOW() - INTERVAL '7 days'
        ORDER BY n.created_at DESC
        LIMIT :lim
    """, {"lim": limit})
    logger.info(f"Daily enrichment: {len(rows)} articles to enrich")
    for r in rows:
        try:
            await enrich_article(str(r["id"]), r["title"], r["text"], r.get("source_name", ""))
        except Exception as e:
            logger.error(f"Batch enrichment error: {e}")


async def run_daily_enrichment(limit: int = 100):
    cfg = load_config()
    llm_cfg = cfg.get("llm", {})
    batch_limit = int(llm_cfg.get("batch_limit", limit))
    if llm_cfg.get("enable_enrichment", True):
        await _batch_enrichment(batch_limit)


async def run_daily_scheduler(shutdown_event):
    cfg = load_config()
    interval = int(cfg.get("llm", {}).get("daily_interval_seconds", 86400))
    logger.info(f"Daily enrichment scheduler started (interval={interval}s)")

    await asyncio.sleep(30)
    while not shutdown_event.is_set():
        try:
            logger.info("Daily enrichment cycle starting...")
            await run_daily_enrichment()
            logger.info("Daily enrichment cycle complete")
        except Exception as e:
            logger.error(f"Daily enrichment cycle error: {e}")
        try:
            await asyncio.wait_for(asyncio.shield(shutdown_event.wait()), timeout=interval)
            break
        except asyncio.TimeoutError:
            pass
