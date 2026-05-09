import json
import logging
import os
from db.pool import execute_sql
from utils.config import load_config

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        from langchain_openai import ChatOpenAI
        config = load_config()
        _llm = ChatOpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1",
            model=config["llm"]["enrichment_model"],
            temperature=config["llm"]["enrichment_temperature"],
            max_tokens=500,
        )
    return _llm


async def enrich_article(article_id: str, title: str, text: str, source_name: str = ""):
    if not load_config()["llm"].get("enable_enrichment", True):
        return
    if not text and not title:
        return

    prompt = f"""Analyze this financial news article for macro-economic impact.

Title: {title}
Source: {source_name}
Text (excerpt): {text[:800]}

Respond with ONLY valid JSON, no other text:
{{"region": "<US|Europe|Asia-Pacific|Americas|Global>", "currency_tag": "<USD|EUR|GBP|JPY|CHF|AUD|CAD|null>", "event_category": "<central-bank|earnings|gdp|trade|employment|inflation|geopolitical|other>", "predicted_direction": "<up|down|neutral>", "predicted_magnitude": <float 0.0-5.0>, "market_reasoning": "<one paragraph explaining expected market impact>"}}"""

    try:
        llm = _get_llm()
        response = await llm.ainvoke(prompt)
        content = response.content.strip()
        if "```" in content:
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        data = json.loads(content)
        region = data.get("region", "Global")
        currency = data.get("currency_tag")
        if currency == "null":
            currency = None
        category = data.get("event_category", "other")
        direction = data.get("predicted_direction", "neutral")
        if direction not in ("up", "down", "neutral"):
            direction = "neutral"
        magnitude = float(data.get("predicted_magnitude", 0))
        magnitude = max(0.0, min(5.0, magnitude))
        reasoning = data.get("market_reasoning", "")

        config = load_config()
        execute_sql("""
            UPDATE macro_news SET
                region = :region, currency_tag = :currency,
                event_category = :category, predicted_direction = :direction,
                predicted_magnitude = :magnitude, market_reasoning = :reasoning,
                model_used = :model, enriched_at = NOW()
            WHERE id = :id
        """, {
            "region": region, "currency": currency,
            "category": category, "direction": direction,
            "magnitude": magnitude, "reasoning": reasoning,
            "model": config["llm"]["enrichment_model"],
            "id": article_id,
        })
        logger.info(f"Enriched: {title[:50]}... -> {region}/{currency}/{direction}")
    except Exception as e:
        logger.error(f"Enrichment failed for {title[:50]}: {e}")
