import asyncio
import logging

logger = logging.getLogger(__name__)


def _scrape_with_newspaper(url: str) -> dict:
    from newspaper import Article
    article = Article(url)
    article.download()
    article.parse()
    return {
        "full_text": article.text,
        "author": ", ".join(article.authors) if article.authors else "",
        "word_count": len(article.text.split()) if article.text else 0,
    }


async def scrape_article(url: str) -> dict:
    try:
        result = await asyncio.to_thread(_scrape_with_newspaper, url)
        return result
    except Exception as e:
        logger.warning(f"Scrape failed for {url}: {e}")
        return {"full_text": "", "author": "", "word_count": 0}
