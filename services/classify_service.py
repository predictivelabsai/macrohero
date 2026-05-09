import logging
from db.pool import execute_sql
from utils.config import get_event_categories

logger = logging.getLogger(__name__)


def classify_article(title: str, summary: str, full_text: str = "") -> list[dict]:
    text_lower = f"{title} {summary} {full_text[:500]}".lower()
    categories = get_event_categories()
    matches = []

    for cat in categories:
        keywords = cat.get("keywords", [])
        hit_count = sum(1 for kw in keywords if kw.lower() in text_lower)
        if hit_count > 0:
            relevance = min(1.0, hit_count / max(len(keywords) * 0.3, 1))
            matches.append({
                "slug": cat["slug"],
                "relevance_score": round(relevance, 2),
            })

    if not matches:
        matches.append({"slug": "geopolitical", "relevance_score": 0.1})

    return matches


def save_news_categories(news_id: str, category_matches: list[dict]):
    for match in category_matches:
        try:
            execute_sql("""
                INSERT INTO news_categories (news_id, category_id, relevance_score)
                SELECT :nid, c.id, :score
                FROM event_categories c WHERE c.slug = :slug
                ON CONFLICT (news_id, category_id) DO NOTHING
            """, {
                "nid": news_id,
                "slug": match["slug"],
                "score": match["relevance_score"],
            })
        except Exception as e:
            logger.error(f"Failed to save category link: {e}")


def get_trending_categories(hours: int = 24) -> list[dict]:
    from db.pool import fetch_all
    return fetch_all("""
        SELECT c.name, c.slug, c.color, c.icon, COUNT(nc.news_id) AS article_count
        FROM event_categories c
        JOIN news_categories nc ON nc.category_id = c.id
        JOIN macro_news n ON n.id = nc.news_id
        WHERE n.created_at > NOW() - make_interval(hours => :hours)
        GROUP BY c.id, c.name, c.slug, c.color, c.icon
        ORDER BY article_count DESC
    """, {"hours": hours})
