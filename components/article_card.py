from fasthtml.common import *
from monsterui.all import *


_DIR_COLORS = {"up": "#10b981", "down": "#ef4444", "neutral": "#6b7280"}
_DIR_ARROWS = {"up": "↑", "down": "↓", "neutral": "→"}

_REGION_COLORS = {
    "US": "#3b82f6", "Europe": "#8b5cf6", "Asia-Pacific": "#f59e0b",
    "Americas": "#10b981", "Global": "#6b7280",
}


def _direction_badge(direction, magnitude):
    direction = (direction or "neutral").lower()
    color = _DIR_COLORS.get(direction, "#6b7280")
    arrow = _DIR_ARROWS.get(direction, "")
    mag_text = f"{magnitude:+.2f}%" if magnitude is not None else ""
    return Span(
        f"{arrow} {mag_text}",
        style=f"background:{color}; color:white; font-size:0.6rem; padding:1px 6px; border-radius:4px; font-weight:700;",
    )


def _region_chip(region):
    if not region:
        return None
    color = _REGION_COLORS.get(region, "#6b7280")
    return Span(
        region,
        style=f"color:{color}; font-size:0.6rem; font-weight:600; border:1px solid {color}; padding:0 4px; border-radius:3px;",
    )


def _currency_chip(currency):
    if not currency:
        return None
    return Span(
        currency,
        style="color:#1e40af; font-size:0.6rem; font-weight:700; background:#eff6ff; padding:0 4px; border-radius:3px;",
    )


def MacroArticleCard(article: dict):
    title = article.get("title", "Untitled")
    url = article.get("url", "#")
    source_name = article.get("source_name", "")
    author = article.get("author", "")
    pub_date = article.get("published_at", "")
    if pub_date and hasattr(pub_date, "strftime"):
        pub_date = pub_date.strftime("%H:%M")

    direction = article.get("predicted_direction")
    magnitude = article.get("predicted_magnitude")
    region = article.get("region")
    currency = article.get("currency_tag")
    reasoning = article.get("market_reasoning", "")

    dir_badge = _direction_badge(direction, magnitude) if direction else None

    return Div(
        DivLAligned(
            dir_badge,
            A(Strong(title, cls="text-sm"), href=url, target="_blank", cls="no-underline hover:underline"),
            cls="gap-2",
        ),
        DivLAligned(
            _region_chip(region),
            _currency_chip(currency),
            Small(source_name, cls="feed-meta") if source_name else None,
            Small(f"by {author}", cls="feed-meta") if author else None,
            Small(pub_date, cls="feed-meta") if pub_date else None,
            cls="gap-2 mt-1 flex-wrap",
        ),
        Small(reasoning[:120] + ("..." if len(reasoning) > 120 else ""), cls="text-xs", style="color:#6b7280; display:block; margin-top:2px;") if reasoning else None,
        cls="feed-item",
    )
