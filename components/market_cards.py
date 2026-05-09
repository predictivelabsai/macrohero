from fasthtml.common import *
from monsterui.all import *


def CurrencyPairCard(pair: dict, news: list[dict]):
    pair_name = pair["pair"]
    base = pair["base"]
    quote = pair["quote"]

    news_items = []
    for n in news[:5]:
        direction = (n.get("predicted_direction") or "neutral").lower()
        color = {"up": "#10b981", "down": "#ef4444"}.get(direction, "#6b7280")
        arrow = {"up": "↑", "down": "↓"}.get(direction, "→")
        mag = n.get("predicted_magnitude")
        mag_text = f" {mag:+.2f}%" if mag is not None else ""
        news_items.append(
            Div(
                DivLAligned(
                    Span(f"{arrow}{mag_text}", style=f"color:{color}; font-size:0.7rem; font-weight:700; min-width:55px;"),
                    Span(n.get("title", "")[:60] + ("..." if len(n.get("title", "")) > 60 else ""), cls="text-xs"),
                    cls="gap-2",
                ),
                cls="py-0.5",
            )
        )

    if not news_items:
        news_items = [P("No recent news.", cls="text-xs text-muted")]

    return Card(
        DivFullySpaced(
            DivLAligned(
                Span(pair_name, cls="text-base font-bold"),
                Span(f"{base}/{quote}", cls="text-xs text-muted"),
                cls="gap-2",
            ),
        ),
        Div(*news_items, cls="mt-2"),
        cls="mb-3",
    )


def MarketMoverRow(article: dict):
    title = article.get("title", "Untitled")
    url = article.get("url", "#")
    direction = (article.get("predicted_direction") or "neutral").lower()
    magnitude = article.get("predicted_magnitude")
    currency = article.get("currency_tag", "")
    source = article.get("source_name", "")
    reasoning = article.get("market_reasoning", "")

    color = {"up": "#10b981", "down": "#ef4444"}.get(direction, "#6b7280")
    arrow = {"up": "↑", "down": "↓"}.get(direction, "→")
    mag_text = f"{magnitude:+.2f}%" if magnitude is not None else ""

    return Div(
        DivLAligned(
            Span(f"{arrow} {mag_text}", style=f"background:{color}; color:white; font-size:0.65rem; padding:1px 6px; border-radius:4px; font-weight:700; min-width:60px; text-align:center;"),
            Span(currency, style="color:#1e40af; font-size:0.65rem; font-weight:700; background:#eff6ff; padding:0 4px; border-radius:3px;") if currency else None,
            A(Strong(title[:80], cls="text-sm"), href=url, target="_blank", cls="no-underline hover:underline"),
            cls="gap-2",
        ),
        DivLAligned(
            Small(source, cls="feed-meta") if source else None,
            Small(reasoning[:100] + ("..." if len(reasoning) > 100 else ""), style="font-size:0.7rem; color:#6b7280;") if reasoning else None,
            cls="gap-2 mt-1",
        ),
        cls="py-2 border-b",
        style="border-color: #f3f4f6;",
    )
