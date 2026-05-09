from fasthtml.common import *
from monsterui.all import *
from dotenv import load_dotenv
import asyncio
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()

APP_VERSION = "0.1.0"

from utils.config import load_config, get_event_categories, get_category_by_slug
from db.pool import fetch_all, fetch_one, execute_sql

config = load_config()

sse_script = Script(src="https://unpkg.com/htmx-ext-sse@2.2.3/sse.js")
favicon_link = Link(rel="icon", type="image/svg+xml", href="/static/favicon.svg")

app, rt = fast_app(
    hdrs=(
        Theme.blue.headers(highlightjs=True),
        sse_script,
        favicon_link,
        Style("""
            html, body { overflow-x: hidden; max-width: 100vw; }
            .app-layout { display: flex; gap: 0; height: calc(100vh - 48px); overflow: hidden; }
            .left-pane { width: 240px; min-width: 240px; overflow-y: auto; padding: 0; background: #0f172a; display: flex; flex-direction: column; }
            .center-pane { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
            .right-pane { width: 320px; min-width: 320px; overflow-y: auto; padding: 12px; background: #f8fafc; border-left: 1px solid #e5e7eb; }

            .feed-area { flex: 1; overflow-y: auto; padding: 16px; }
            .chat-input-area { padding: 12px 16px; border-top: 1px solid #e5e7eb; }
            .chat-input-area .uk-input { border-radius: 24px; padding-left: 16px; }
            .chat-input-area .uk-input:focus { box-shadow: 0 0 0 2px rgba(59,130,246,0.3); border-color: #3b82f6; }

            #chat-messages { overflow-y: auto; padding: 0 16px; }
            #chat-messages:empty { display: none; }

            .sidebar-topic { cursor: pointer; padding: 6px 12px; border-radius: 6px; border-left: none;
                             transition: background 0.15s; margin-bottom: 2px; color: #e2e8f0; }
            .sidebar-topic:hover { background: rgba(255,255,255,0.06); color: #f8fafc; }
            .sidebar-topic.active { background: #1e293b; color: #f8fafc; }

            .chat-user { background: #eff6ff; border-radius: 12px; padding: 10px 16px; margin: 6px 0; max-width: 80%; margin-left: auto; }
            .chat-assistant { background: #f8f9fa; border-radius: 12px; padding: 12px 16px; margin: 6px 0; max-width: 90%; }
            .chat-assistant h1, .chat-assistant h2, .chat-assistant h3 { margin-top: 0.75rem; margin-bottom: 0.25rem; font-size: 1rem; font-weight: 600; }
            .chat-assistant ul, .chat-assistant ol { margin: 0.25rem 0; padding-left: 1.25rem; }
            .chat-assistant li { margin-bottom: 0.15rem; }
            .chat-assistant p { margin: 0.25rem 0; }
            .chat-assistant a { color: #2563eb; text-decoration: underline; }
            .chat-assistant strong { font-weight: 600; }

            .sentiment-positive { color: #10b981; font-weight: 600; }
            .sentiment-negative { color: #ef4444; font-weight: 600; }
            .sentiment-neutral { color: #6b7280; font-weight: 600; }
            .feed-item { border-left: 3px solid #3b82f6; padding-left: 10px; margin-bottom: 10px; }
            .feed-meta { color: #4b5563 !important; font-weight: 500; }

            .thinking-indicator { display: flex; align-items: center; gap: 8px; color: #6b7280; font-size: 0.85rem; padding: 8px 16px; }
            .thinking-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #3b82f6; animation: pulse 1.4s ease-in-out infinite; }
            .thinking-dot:nth-child(2) { animation-delay: 0.2s; }
            .thinking-dot:nth-child(3) { animation-delay: 0.4s; }
            @keyframes pulse { 0%,80%,100% { opacity:0.3; transform:scale(0.8); } 40% { opacity:1; transform:scale(1.2); } }

            .app-nav { display: flex; align-items: center; justify-content: space-between; padding: 8px 20px; background: #0f172a; height: 48px; }

            .sidebar-section { margin-bottom: 4px; padding: 0 8px; }
            .sidebar-section-title { font-size: 0.65rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #64748b; margin-bottom: 4px; padding-left: 12px; padding-top: 8px; }

            .sidebar-logo { padding: 12px 16px; border-bottom: 1px solid rgba(255,255,255,0.06); }
            .sidebar-footer { padding: 8px 16px; border-top: 1px solid rgba(255,255,255,0.06); margin-top: auto; }

            .sidebar-shortcut { display: block; padding: 4px 12px 4px 28px; font-size: 0.72rem; color: #94a3b8; cursor: pointer;
                                transition: background 0.15s, color 0.15s; border-radius: 4px; text-decoration: none; margin-bottom: 1px; }
            .sidebar-shortcut:hover { background: rgba(255,255,255,0.06); color: #e2e8f0; }

            .sidebar-expander { display: flex; align-items: center; justify-content: space-between; padding: 6px 12px;
                                cursor: pointer; color: #64748b; font-size: 0.65rem; font-weight: 600; text-transform: uppercase;
                                letter-spacing: 0.05em; user-select: none; }
            .sidebar-expander:hover { color: #94a3b8; }
            .sidebar-expander .chevron { transition: transform 0.2s; }
            .sidebar-expander .chevron.collapsed { transform: rotate(-90deg); }

            .greeting-text { font-size: 1.5rem; font-weight: 700; color: #1e293b; margin-bottom: 4px; }
            .greeting-sub { font-size: 0.9rem; color: #64748b; margin-bottom: 8px; }

            .starter-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
            .starter-card { cursor: pointer; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 12px;
                            font-size: 0.8rem; transition: all 0.15s; }
            .starter-card:hover { background: #eff6ff; border-color: #3b82f6; box-shadow: 0 2px 8px rgba(59,130,246,0.1); }

            .mobile-tabs { display: none; }
            @media (max-width: 768px) {
                .left-pane { display: none; position: fixed; top: 48px; left: 0; bottom: 0; z-index: 50; background: #0f172a; width: 85vw; box-shadow: 2px 0 12px rgba(0,0,0,0.3); }
                .left-pane.mobile-open { display: flex; flex-direction: column; }
                .right-pane { display: none; position: fixed; top: 48px; right: 0; bottom: 0; z-index: 50; background: #f8fafc; width: 85vw; box-shadow: -2px 0 12px rgba(0,0,0,0.15); }
                .right-pane.mobile-open { display: block; }
                .mobile-tabs { display: flex; justify-content: space-around; border-bottom: 1px solid #e5e7eb; padding: 6px 0; }
                .mobile-tabs button { background: none; border: none; font-size: 0.75rem; padding: 4px 12px; cursor: pointer; color: #6b7280; }
                .mobile-tabs button:hover { color: #1e40af; }
                .mobile-overlay { display: none; position: fixed; inset: 0; z-index: 40; background: rgba(0,0,0,0.3); }
                .mobile-overlay.active { display: block; }
                .app-layout { height: calc(100vh - 48px); }
                .starter-grid { grid-template-columns: 1fr; }
            }
        """),
    ),
    pico=False,
)

shutdown_event = signal_shutdown()

article_queue: asyncio.Queue = asyncio.Queue()
category_queues: dict[str, asyncio.Queue] = {}

from components.article_card import MacroArticleCard
from components.chat_ui import ChatMessageBubble
from components.layout import NavBar_


# ===================== HELPERS =====================

def _get_session_user(sess) -> dict | None:
    uid = sess.get("user_id")
    if not uid:
        return None
    return {"id": uid, "name": sess.get("user_name", "")}


def _create_new_session(category_slug: str = None, user_id: str = None) -> dict:
    result = fetch_one("""
        INSERT INTO chat_sessions (category_slug, user_id) VALUES (:slug, :uid) RETURNING id, category_slug, title, created_at
    """, {"slug": category_slug, "uid": user_id})
    return result


def _generate_chat_title(msg: str) -> str:
    return msg[:40] + ("..." if len(msg) > 40 else "")


def _get_categories_with_counts() -> list[dict]:
    categories = get_event_categories()
    counts = fetch_all("""
        SELECT c.slug, COUNT(nc.news_id) AS article_count
        FROM event_categories c
        LEFT JOIN news_categories nc ON nc.category_id = c.id
        LEFT JOIN macro_news n ON n.id = nc.news_id AND n.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY c.slug
    """)
    count_map = {r["slug"]: r["article_count"] for r in counts}
    for cat in categories:
        cat["article_count"] = count_map.get(cat["slug"], 0)
    return categories


def _get_recent_articles(limit: int = 20) -> list[dict]:
    return fetch_all("""
        SELECT n.id, n.title, n.url, n.author, n.published_at,
               n.region, n.currency_tag, n.event_category,
               n.predicted_direction, n.predicted_magnitude, n.market_reasoning,
               s.name AS source_name
        FROM macro_news n
        LEFT JOIN sources s ON s.id = n.source_id
        ORDER BY n.created_at DESC LIMIT :limit
    """, {"limit": limit})


def _chat_history_items(active_session_id: str, user_id: str = None) -> list:
    if not user_id:
        return []
    sessions = fetch_all("""
        SELECT id, title, created_at FROM chat_sessions
        WHERE user_id = :uid
        ORDER BY updated_at DESC LIMIT 8
    """, {"uid": user_id})
    items = []
    for s in sessions:
        is_active = str(s["id"]) == active_session_id
        ts = s["created_at"].strftime("%H:%M") if hasattr(s["created_at"], "strftime") else ""
        title = s["title"][:22] + ("..." if len(s["title"]) > 22 else "")
        active_style = "background:rgba(59,130,246,0.15);" if is_active else ""
        items.append(
            A(
                DivFullySpaced(
                    DivLAligned(UkIcon("message-circle", height=10, style="color:#64748b;"), Span(title, style="color:#cbd5e1; font-size:0.72rem;"), cls="gap-1"),
                    Span(ts, style="font-size:0.55rem; color:#64748b;"),
                ),
                href=f"/session/{s['id']}",
                cls="no-underline block",
                style=f"padding:4px 8px; border-radius:4px; {active_style}",
            )
        )
    return items


def _sidebar_category(cat: dict, active: bool = False):
    count = cat.get("article_count", 0)
    return A(
        DivLAligned(
            UkIcon(cat["icon"], height=14, style=f"color:{cat['color']};"),
            Div(
                Span(cat["name"], style="font-size:0.8rem; color:#e2e8f0;"),
                Span(f" ({count})", style="font-size:0.65rem; color:#64748b;"),
            ),
            cls="gap-2",
        ),
        href=f"/category/{cat['slug']}",
        cls="sidebar-topic no-underline" + (" active" if active else ""),
    )


def _starter_cards(session_id: str):
    starters = [
        ("Give me FX strategies for a Hormuz deal scenario", "globe"),
        ("Backtest momentum on EUR/USD over last year", "bar-chart-2"),
        ("Short USD/JPY — backtest with 1% TP, 0.5% SL", "trending-up"),
        ("What's moving markets today?", "zap"),
        ("US Treasury vs EUR/USD chart", "landmark"),
        ("Show me top market movers", "activity"),
    ]
    cards = []
    for question, icon in starters:
        cards.append(
            Div(
                DivLAligned(UkIcon(icon, height=14), Span(question), cls="gap-2"),
                cls="starter-card",
                onclick=f"var inp=document.getElementById('chat-input'); inp.value={repr(question)}; inp.disabled=false; inp.form.requestSubmit(); this.closest('.starter-grid').remove();",
            )
        )
    return Div(*cards, cls="starter-grid")


def _greeting_message():
    from datetime import datetime
    hour = datetime.now().hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    else:
        greeting = "Good evening"
    return greeting


def _shortcut_item(label: str, command: str):
    return A(
        label,
        href="#",
        cls="sidebar-shortcut",
        onclick=f"var inp=document.getElementById('chat-input'); inp.value={repr(command)}; inp.disabled=false; inp.form.requestSubmit(); return false;",
    )


def _expander_section(title: str, section_id: str, items: list, collapsed: bool = True):
    display = "none" if collapsed else "block"
    chevron_cls = "chevron collapsed" if collapsed else "chevron"
    return Div(
        Div(
            Span(title),
            UkIcon("chevron-down", height=10, cls=chevron_cls, id=f"{section_id}-chevron"),
            cls="sidebar-expander",
            onclick=f"var el=document.getElementById('{section_id}-items'); var ch=document.getElementById('{section_id}-chevron'); if(el.style.display==='none'){{el.style.display='block';ch.classList.remove('collapsed');}}else{{el.style.display='none';ch.classList.add('collapsed');}}",
        ),
        Div(*items, id=f"{section_id}-items", style=f"display:{display};"),
    )


def _upcoming_events_widget():
    events = _get_upcoming_events()
    if not events:
        return P("No upcoming events.", style="font-size:0.72rem; color:#64748b; padding:4px 12px;")
    items = []
    for ev in events[:6]:
        date_str = ev.get("date", "")
        items.append(
            Div(
                DivFullySpaced(
                    Span(ev.get("name", ""), style="font-size:0.72rem; color:#e2e8f0; line-height:1.2; font-weight:500;"),
                    Span(ev.get("country", ""), style="font-size:0.65rem; color:#94a3b8;"),
                ),
                DivFullySpaced(
                    Span(date_str, style="font-size:0.65rem; color:#94a3b8;"),
                    Span(ev.get("impact", ""), style=f"font-size:0.65rem; font-weight:600; color:{'#ef4444' if ev.get('impact')=='High' else '#f59e0b' if ev.get('impact')=='Medium' else '#64748b'};"),
                ),
                style="padding:4px 12px; border-bottom:1px solid rgba(255,255,255,0.06);",
            )
        )
    return Div(*items, id="upcoming-events",
               hx_get="/api/events", hx_trigger="every 300s", hx_swap="outerHTML")


_events_cache = {"data": [], "fetched_at": 0}


def _get_upcoming_events() -> list[dict]:
    import time
    now = time.time()
    if _events_cache["data"] and (now - _events_cache["fetched_at"]) < 600:
        return _events_cache["data"]

    api_key = os.environ.get("EODHD_API_KEY")
    if not api_key:
        return []
    try:
        import httpx
        from datetime import datetime, timedelta
        today = datetime.now().strftime("%Y-%m-%d")
        end = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        url = f"https://eodhd.com/api/economic-events?api_token={api_key}&from={today}&to={end}&fmt=json"
        resp = httpx.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        events = []
        for ev in data[:20]:
            impact = "High" if ev.get("importance", 0) >= 3 else "Medium" if ev.get("importance", 0) >= 2 else "Low"
            events.append({
                "name": ev.get("event", "Unknown"),
                "country": ev.get("country", ""),
                "date": ev.get("date", "")[:10],
                "impact": impact,
            })
        _events_cache["data"] = events
        _events_cache["fetched_at"] = now
        return events
    except Exception:
        return _events_cache["data"]


# ===================== ROUTES =====================

@rt
def index(req, sess):
    user = _get_session_user(sess)
    if not user:
        from modules.landing import landing_page
        return landing_page()
    chat_sess = _create_new_session("general", user_id=user["id"])
    return _app_shell(chat_sess, user=user)


@rt("/category/{category_slug}")
def category_view(category_slug: str, sess):
    user = _get_session_user(sess)
    uid = user["id"] if user else None
    chat_sess = _create_new_session(category_slug, user_id=uid)
    return _app_shell(chat_sess, active_category=category_slug, user=user)


@rt("/session/{session_id}")
def load_session(session_id: str, sess):
    user = _get_session_user(sess)
    chat_sess = fetch_one("SELECT id, category_slug, title, created_at FROM chat_sessions WHERE id = :sid", {"sid": session_id})
    if not chat_sess:
        return RedirectResponse("/", status_code=303)
    return _app_shell(chat_sess, user=user)


@rt("/view/movers")
def view_movers():
    from components.market_cards import MarketMoverRow
    articles = fetch_all("""
        SELECT n.title, n.url, n.region, n.currency_tag, n.event_category,
               n.predicted_direction, n.predicted_magnitude, n.market_reasoning,
               s.name AS source_name
        FROM macro_news n LEFT JOIN sources s ON s.id = n.source_id
        WHERE n.created_at > NOW() - INTERVAL '24 hours'
          AND n.predicted_magnitude IS NOT NULL
        ORDER BY ABS(n.predicted_magnitude) DESC LIMIT 20
    """)
    if not articles:
        return Div(H3("Market Movers (24h)", cls="text-lg font-semibold mb-3"),
                   P("No enriched articles yet. News will be enriched automatically.", cls="text-sm text-muted"))
    return Div(
        H3("Market Movers (24h)", cls="text-lg font-semibold mb-3"),
        *[MarketMoverRow(a) for a in articles],
    )


@rt("/view/pairs")
def view_pairs():
    from components.market_cards import CurrencyPairCard
    from utils.config import get_currency_pairs
    pairs = get_currency_pairs()
    pair_cards = []
    for p in pairs:
        news = fetch_all("""
            SELECT title, predicted_direction, predicted_magnitude, published_at
            FROM macro_news
            WHERE currency_tag IN (:base, :quote)
              AND created_at > NOW() - INTERVAL '24 hours'
            ORDER BY created_at DESC LIMIT 5
        """, {"base": p["base"], "quote": p["quote"]})
        pair_cards.append(CurrencyPairCard(p, news))
    return Div(H3("Currency Pairs", cls="text-lg font-semibold mb-3"), *pair_cards)


@rt("/view/history")
def view_history(page: int = 1, category: str = ""):
    per_page = 25
    offset = (page - 1) * per_page
    if category:
        articles = fetch_all("""
            SELECT n.title, n.url, n.region, n.currency_tag, n.event_category,
                   n.predicted_direction, n.predicted_magnitude, n.published_at,
                   s.name AS source_name
            FROM macro_news n LEFT JOIN sources s ON s.id = n.source_id
            WHERE n.event_category = :cat
            ORDER BY n.created_at DESC LIMIT :lim OFFSET :off
        """, {"cat": category, "lim": per_page, "off": offset})
    else:
        articles = fetch_all("""
            SELECT n.title, n.url, n.region, n.currency_tag, n.event_category,
                   n.predicted_direction, n.predicted_magnitude, n.published_at,
                   s.name AS source_name
            FROM macro_news n LEFT JOIN sources s ON s.id = n.source_id
            ORDER BY n.created_at DESC LIMIT :lim OFFSET :off
        """, {"lim": per_page, "off": offset})

    rows = []
    for a in articles:
        pub = a["published_at"].strftime("%Y-%m-%d %H:%M") if a.get("published_at") and hasattr(a["published_at"], "strftime") else ""
        rows.append(Tr(
            Td(A(a["title"][:60], href=a.get("url", "#"), target="_blank", cls="text-xs no-underline hover:underline")),
            Td(Span(a.get("region", ""), cls="text-xs")),
            Td(Span(a.get("currency_tag", ""), cls="text-xs")),
            Td(Span(a.get("event_category", ""), cls="text-xs")),
            Td(Span(pub, cls="text-xs")),
            Td(Span(a.get("source_name", ""), cls="text-xs")),
        ))

    prev_btn = A("Previous", hx_get=f"/view/history?page={page-1}&category={category}", hx_target="#center-content", hx_swap="innerHTML",
                  cls="uk-button uk-button-default uk-button-small") if page > 1 else None
    next_btn = A("Next", hx_get=f"/view/history?page={page+1}&category={category}", hx_target="#center-content", hx_swap="innerHTML",
                  cls="uk-button uk-button-default uk-button-small") if len(articles) == per_page else None

    return Div(
        H3("News History", cls="text-lg font-semibold mb-3"),
        Table(
            Thead(Tr(Th("Title"), Th("Region"), Th("Currency"), Th("Category"), Th("Published"), Th("Source"))),
            Tbody(*rows),
            cls="uk-table uk-table-small uk-table-striped",
        ) if rows else P("No articles found.", cls="text-sm text-muted"),
        DivFullySpaced(prev_btn, next_btn, cls="mt-3") if (prev_btn or next_btn) else None,
    )


@rt("/api/events")
def api_events():
    return _upcoming_events_widget()


@rt("/api/clear-history", methods=["POST"])
def api_clear_history():
    execute_sql("DELETE FROM chat_messages")
    execute_sql("DELETE FROM chat_sessions")
    return RedirectResponse("/", status_code=303)


# ===================== CHAT ROUTES =====================

@rt("/chat/{session_id}/send", methods=["POST"])
async def chat_send(session_id: str, msg: str, req, sess, website: str = ""):
    from utils.auth import get_client_ip
    from utils.rate_limit import check_rate_limit

    if website:
        return Div(hx_swap_oob="beforeend:#chat-messages")

    sec_cfg = config.get("security", {})
    max_req = int(sec_cfg.get("chat_rate_limit_max", 10))
    window = int(sec_cfg.get("chat_rate_limit_window_seconds", 600))
    client_ip = get_client_ip(req)
    if not check_rate_limit(f"chat:{client_ip}", max_req, window):
        return Div(Div(P("Too many requests. Please wait.", cls="text-sm"), cls="p-3"),
                   cls="chat-assistant", hx_swap_oob="beforeend:#chat-messages")

    user = _get_session_user(sess)
    if not user:
        anon_limit = int(sec_cfg.get("anon_chat_limit", 3))
        count = int(sess.get("anon_chat_count", 0))
        if count >= anon_limit:
            return Div(
                Div(
                    P("Register to continue chatting", cls="font-semibold text-sm"),
                    P("Free accounts get unlimited macro analysis.", cls="text-sm text-muted mt-1"),
                    DivLAligned(
                        A("Register", href="/register", cls="uk-button uk-button-primary uk-button-small"),
                        A("Login", href="/login", cls="uk-button uk-button-default uk-button-small"),
                        cls="gap-2 mt-3",
                    ),
                    cls="p-3",
                ),
                cls="chat-assistant", hx_swap_oob="beforeend:#chat-messages",
            )
        sess["anon_chat_count"] = count + 1

    execute_sql("""
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (:sid, 'user', :content)
    """, {"sid": session_id, "content": msg})
    title = _generate_chat_title(msg)
    execute_sql("""
        UPDATE chat_sessions SET title = :title, updated_at = NOW()
        WHERE id = :sid AND title = 'New chat'
    """, {"sid": session_id, "title": title})

    user_bubble = ChatMessageBubble("user", msg)
    thinking = Div(
        Div(
            Span("", cls="thinking-dot"), Span("", cls="thinking-dot"), Span("", cls="thinking-dot"),
            Span("Thinking...", id="thinking-text"),
            cls="thinking-indicator",
        ),
        id="thinking-indicator",
    )
    response_area = Div(
        id=f"response-{session_id}",
        hx_ext="sse",
        sse_connect=f"/sse/chat/{session_id}",
        sse_swap="token",
        sse_close="done",
        hx_swap="beforeend",
    )
    return Div(user_bubble, thinking, response_area, hx_swap_oob="beforeend:#chat-messages")


# ===================== SSE ENDPOINTS =====================

@rt("/sse/feed")
async def sse_feed():
    return EventStream(_feed_generator())

@rt("/sse/feed/{category_slug}")
async def sse_feed_category(category_slug: str):
    return EventStream(_feed_generator(category_slug))

@rt("/sse/chat/{session_id}")
async def sse_chat(session_id: str):
    messages = fetch_all("""
        SELECT role, content FROM chat_messages
        WHERE session_id = :sid ORDER BY created_at ASC
    """, {"sid": session_id})
    sess = fetch_one("SELECT category_slug FROM chat_sessions WHERE id = :sid", {"sid": session_id})
    category_slug = sess["category_slug"] if sess else None
    return EventStream(_chat_stream(session_id, messages, category_slug))


# ===================== SSE GENERATORS =====================

async def _feed_generator(category_slug: str = None):
    q = category_queues.get(category_slug, article_queue) if category_slug else article_queue
    while not shutdown_event.is_set():
        try:
            article = await asyncio.wait_for(q.get(), timeout=20.0)
            card = MacroArticleCard(article)
            yield sse_message(card, event="new-article")
        except asyncio.TimeoutError:
            yield ": keepalive\n\n"


_MOVERS_KEYWORDS = ["market movers", "top movers", "what's moving", "biggest movers"]


def _is_movers_request(messages: list[dict]) -> bool:
    if not messages:
        return False
    last = messages[-1]
    if last.get("role") != "user":
        return False
    text = last.get("content", "").strip().lower()
    return any(kw in text for kw in _MOVERS_KEYWORDS)


async def _chat_stream(session_id: str, messages: list[dict], category_slug: str = None):
    if _is_movers_request(messages):
        async for msg in _movers_stream(session_id):
            yield msg
        return

    from services.chat_service import get_chat_response_stream
    full_response = ""
    backtest_streaming = False
    try:
        async for event in get_chat_response_stream(messages, category_slug):
            if event["type"] == "status":
                yield sse_message(
                    Script(f"document.getElementById('thinking-text').textContent='{event['text']}';"),
                    event="token",
                )
            elif event["type"] == "backtest_header":
                backtest_streaming = True
                yield sse_message(
                    Div(
                        Script("var el=document.getElementById('thinking-indicator'); if(el) el.remove();"),
                        Div(NotStr(event["html"]), cls="chat-assistant text-sm", id="bt-stream-container"),
                    ),
                    event="token",
                )
            elif event["type"] == "backtest_trade":
                yield sse_message(
                    Script(f"document.getElementById('bt-live-body').insertAdjacentHTML('beforeend','{event['html'].replace(chr(39), chr(92)+chr(39))}');"),
                    event="token",
                )
            elif event["type"] == "token":
                html = event["html"]
                full_response = html
                if backtest_streaming:
                    yield sse_message(
                        Script("var el=document.getElementById('bt-stream-container'); if(el) el.remove();"),
                        event="token",
                    )
                    backtest_streaming = False
                yield sse_message(
                    Div(
                        Script("var el=document.getElementById('thinking-indicator'); if(el) el.remove();"),
                        Div(NotStr(html), cls="chat-assistant text-sm"),
                    ),
                    event="token",
                )
    except Exception as e:
        yield sse_message(
            Div(
                Script("var el=document.getElementById('thinking-indicator'); if(el) el.remove();"),
                Div(NotStr(f'<p class="text-red-500">Error: {e}</p>'), cls="chat-assistant"),
            ),
            event="token",
        )
    if full_response:
        execute_sql("""
            INSERT INTO chat_messages (session_id, role, content)
            VALUES (:sid, 'assistant', :content)
        """, {"sid": session_id, "content": full_response})
    yield sse_message(
        Script("document.getElementById('chat-input').disabled=false; document.getElementById('chat-input').focus();"),
        event="token",
    )
    yield sse_message("", event="done")


async def _movers_stream(session_id: str):
    yield sse_message(
        Script("document.getElementById('thinking-text').textContent='Loading market movers...';"),
        event="token",
    )

    from components.market_cards import MarketMoverRow
    articles = fetch_all("""
        SELECT n.title, n.url, n.region, n.currency_tag,
               n.predicted_direction, n.predicted_magnitude, n.market_reasoning,
               s.name AS source_name
        FROM macro_news n LEFT JOIN sources s ON s.id = n.source_id
        WHERE n.created_at > NOW() - INTERVAL '24 hours'
          AND n.predicted_magnitude IS NOT NULL
        ORDER BY ABS(n.predicted_magnitude) DESC LIMIT 10
    """)

    if articles:
        from fasthtml.common import to_xml
        rows_html = "".join(to_xml(MarketMoverRow(a)) for a in articles)
        full_html = f'<h3 style="font-size:1rem; font-weight:600; margin-bottom:8px;">Top Market Movers (24h)</h3>{rows_html}'
    else:
        full_html = '<p style="color:#6b7280;">No enriched articles found yet. News will be enriched automatically.</p>'

    yield sse_message(
        Div(
            Script("var el=document.getElementById('thinking-indicator'); if(el) el.remove();"),
            Div(NotStr(full_html), cls="chat-assistant"),
        ),
        event="token",
    )
    execute_sql("""
        INSERT INTO chat_messages (session_id, role, content)
        VALUES (:sid, 'assistant', :content)
    """, {"sid": session_id, "content": full_html})
    yield sse_message(
        Script("document.getElementById('chat-input').disabled=false; document.getElementById('chat-input').focus();"),
        event="token",
    )
    yield sse_message("", event="done")


# ===================== AUTH ROUTES =====================

@rt("/login")
def login_page(sess):
    return Title("MacroHero - Login"), NavBar_(), Div(
        Card(
            DivCentered(UkIcon("trending-up", height=32), H2("MacroHero", cls="text-2xl font-bold"),
                        P("Sign in to your account", cls=TextPresets.muted_sm), cls="mb-4"),
            Form(
                Div(Label("Username", fr="username"), Input(name="username", type="text", id="username", placeholder="Username", autocomplete="username", cls="uk-input"), cls="space-y-1"),
                Div(Label("Password", fr="password"), Input(name="password", type="password", id="password", placeholder="Password", autocomplete="current-password", cls="uk-input"), cls="space-y-1 mt-3"),
                Button("Sign in", type="submit", cls=ButtonT.primary + " uk-width-1-1 mt-4"),
                hx_post="/auth/login", hx_target="body",
            ),
            Div(P("No account?", cls="text-sm text-center mt-3"), A("Register", href="/register", cls="uk-button uk-button-text"), cls="text-center"),
            cls="max-w-sm mx-auto mt-12",
        ), cls="flex justify-center p-8",
    )


@rt("/register")
def register_page(sess):
    return Title("MacroHero - Register"), NavBar_(), Div(
        Card(
            DivCentered(UkIcon("trending-up", height=32), H2("MacroHero", cls="text-2xl font-bold"),
                        P("Create your account", cls=TextPresets.muted_sm), cls="mb-4"),
            Form(
                Div(Label("Username", fr="username"), Input(name="username", type="text", id="username", placeholder="Username", autocomplete="username", cls="uk-input"), cls="space-y-1"),
                Div(Label("Password", fr="password"), Input(name="password", type="password", id="password", placeholder="Password", autocomplete="new-password", cls="uk-input"), cls="space-y-1 mt-3"),
                Button("Create account", type="submit", cls=ButtonT.primary + " uk-width-1-1 mt-4"),
                hx_post="/auth/register", hx_target="body",
            ),
            Div(P("Have an account?", cls="text-sm text-center mt-3"), A("Sign in", href="/login", cls="uk-button uk-button-text"), cls="text-center"),
            cls="max-w-sm mx-auto mt-12",
        ), cls="flex justify-center p-8",
    )


@rt("/auth/login", methods=["POST"])
def auth_login(username: str, password: str, sess):
    from utils.auth import verify_password
    username = (username or "").strip().lower()
    user = fetch_one(
        "SELECT id, username, password_hash, display_name FROM users WHERE username = :u",
        {"u": username},
    )
    if not user or not verify_password(password or "", user.get("password_hash") or ""):
        return Div(Card(P("Invalid credentials.", cls="text-sm text-red-600 text-center"),
                        Div(A("Back", href="/login", cls="uk-button uk-button-text"), cls="text-center mt-2"),
                        cls="max-w-sm mx-auto mt-12"), cls="flex justify-center p-8")
    sess["user_id"] = str(user["id"])
    sess["user_name"] = user.get("display_name") or user.get("username") or username
    sess["anon_chat_count"] = 0
    from starlette.responses import Response
    resp = Response(status_code=200)
    resp.headers["HX-Redirect"] = "/"
    return resp


@rt("/auth/register", methods=["POST"])
def auth_register(username: str, password: str, sess):
    from utils.auth import hash_password
    username = (username or "").strip().lower()
    if not username or not password:
        return Div(Card(P("All fields required.", cls="text-sm text-red-600 text-center"),
                        Div(A("Back", href="/register", cls="uk-button uk-button-text"), cls="text-center mt-2"),
                        cls="max-w-sm mx-auto mt-12"), cls="flex justify-center p-8")
    if len(password) < 8:
        return Div(Card(P("Password must be at least 8 characters.", cls="text-sm text-red-600 text-center"),
                        Div(A("Back", href="/register", cls="uk-button uk-button-text"), cls="text-center mt-2"),
                        cls="max-w-sm mx-auto mt-12"), cls="flex justify-center p-8")
    existing = fetch_one("SELECT id FROM users WHERE username = :u", {"u": username})
    if existing:
        return Div(Card(P("Username already taken.", cls="text-sm text-red-600 text-center"),
                        Div(A("Back", href="/register", cls="uk-button uk-button-text"), cls="text-center mt-2"),
                        cls="max-w-sm mx-auto mt-12"), cls="flex justify-center p-8")
    execute_sql(
        "INSERT INTO users (username, password_hash, display_name) VALUES (:u, :h, :d)",
        {"u": username, "h": hash_password(password), "d": username},
    )
    user = fetch_one("SELECT id, username, display_name FROM users WHERE username = :u", {"u": username})
    sess["user_id"] = str(user["id"])
    sess["user_name"] = user.get("display_name") or username
    sess["anon_chat_count"] = 0
    from starlette.responses import Response
    resp = Response(status_code=200)
    resp.headers["HX-Redirect"] = "/"
    return resp


@rt("/auth/logout")
def auth_logout(sess):
    sess.clear()
    return RedirectResponse("/", status_code=303)


# ===================== LAYOUT =====================

def _app_shell(session: dict, active_category: str = None, user: dict = None):
    session_id = str(session["id"])
    categories = _get_categories_with_counts()

    messages = fetch_all("SELECT role, content FROM chat_messages WHERE session_id = :sid ORDER BY created_at ASC", {"sid": session_id})
    recent_articles = _get_recent_articles(20)

    msg_bubbles = [ChatMessageBubble(m["role"], m["content"]) for m in messages]
    if not messages:
        msg_bubbles.append(
            Div(
                P(_greeting_message(), cls="greeting-text"),
                P("I'm your macro-economic market analyst. Ask about FX movements, central bank decisions, trade policy, or backtest a strategy.", cls="greeting-sub"),
                _starter_cards(session_id),
                style="padding: 16px;",
            )
        )

    return (
        Title("MacroHero"),
        NavBar_(user),
        Div(
            Button(UkIcon("menu", height=14), " Menu", onclick="togglePane('left')", cls="text-xs"),
            Button(UkIcon("message-circle", height=14), " Chat", cls="text-xs font-semibold"),
            Button(UkIcon("rss", height=14), " Live Feed", onclick="togglePane('right')", cls="text-xs"),
            cls="mobile-tabs",
        ),
        Div(id="mobile-overlay", cls="mobile-overlay", onclick="closePanes()"),
        Script("""
            function togglePane(side) {
                var left = document.getElementById('left-pane');
                var right = document.getElementById('right-pane');
                var overlay = document.getElementById('mobile-overlay');
                if (side === 'left') {
                    left.classList.toggle('mobile-open');
                    right.classList.remove('mobile-open');
                } else {
                    right.classList.toggle('mobile-open');
                    left.classList.remove('mobile-open');
                }
                overlay.classList.toggle('active', left.classList.contains('mobile-open') || right.classList.contains('mobile-open'));
            }
            function closePanes() {
                document.getElementById('left-pane').classList.remove('mobile-open');
                document.getElementById('right-pane').classList.remove('mobile-open');
                document.getElementById('mobile-overlay').classList.remove('active');
            }
        """),
        Div(
            # LEFT PANE
            Div(
                # Logo
                Div(
                    A(DivLAligned(
                        UkIcon("trending-up", height=16, style="color:#3b82f6;"),
                        Span("MacroHero", style="font-size:0.9rem; font-weight:700; color:#f8fafc;"),
                        cls="gap-2",
                    ), href="/", cls="no-underline"),
                    cls="sidebar-logo",
                ),
                # Home + Threads
                Div(
                    A(
                        DivLAligned(UkIcon("home", height=14, style="color:#94a3b8;"), Span("Home", style="font-size:0.8rem;"), cls="gap-2"),
                        href="/", cls="sidebar-topic no-underline",
                    ),
                    _expander_section("Threads", "threads", [
                        DivFullySpaced(
                            A(
                                DivLAligned(UkIcon("plus", height=10, style="color:#64748b;"), Span("New Chat", style="font-size:0.7rem; color:#94a3b8;"), cls="gap-1"),
                                href="/", cls="no-underline", style="padding:2px 8px;",
                            ),
                            Button(UkIcon("trash-2", height=10, style="color:#64748b;"),
                                   style="background:none; border:none; padding:2px 4px; cursor:pointer;", title="Clear history",
                                   hx_post="/api/clear-history", hx_target="body", hx_confirm="Clear all chat history?"),
                            cls="gap-1",
                            style="padding:0 4px; margin-bottom:4px;",
                        ),
                        *_chat_history_items(session_id, user_id=user["id"] if user else None),
                    ], collapsed=False),
                    cls="sidebar-section",
                ),
                # Trading
                Div(
                    Div("Trading", cls="sidebar-section-title"),
                    A(
                        DivLAligned(UkIcon("zap", height=14, style="color:#f59e0b;"), Span("Market Movers", style="font-size:0.8rem;"), cls="gap-2"),
                        href="#", cls="sidebar-topic no-underline",
                        onclick="var inp=document.getElementById('chat-input'); inp.value='Show me top market movers'; inp.disabled=false; inp.form.requestSubmit(); return false;",
                    ),
                    A(
                        DivLAligned(UkIcon("bar-chart-2", height=14, style="color:#3b82f6;"), Span("Currency Pairs", style="font-size:0.8rem;"), cls="gap-2"),
                        href="/view/pairs", hx_get="/view/pairs", hx_target="#center-content", hx_swap="innerHTML",
                        cls="sidebar-topic no-underline",
                    ),
                    A(
                        DivLAligned(UkIcon("trending-up", height=14, style="color:#10b981;"), Span("Treasury vs FX", style="font-size:0.8rem;"), cls="gap-2"),
                        href="#", cls="sidebar-topic no-underline",
                        onclick="var inp=document.getElementById('chat-input'); inp.value='Show US Treasury 10Y vs EUR/USD chart'; inp.disabled=false; inp.form.requestSubmit(); return false;",
                    ),
                    cls="sidebar-section",
                ),
                # Backtest (AlpaTrade-style expander)
                _expander_section("Backtest", "backtest", [
                    _shortcut_item("EUR/USD momentum 1Y", "Backtest momentum on EUR/USD over last year"),
                    _shortcut_item("GBP/USD momentum 1Y", "Backtest momentum on GBP/USD over last year"),
                    _shortcut_item("Short USD/JPY", "Short USD/JPY — backtest with 1% TP, 0.5% SL"),
                    _shortcut_item("Custom backtest...", "Backtest momentum strategy on "),
                ]),
                # Research (AlpaTrade-style expander)
                _expander_section("Research", "research", [
                    _shortcut_item("FX pair analysis", "Analyze EUR/USD with fundamentals and technicals"),
                    _shortcut_item("Treasury yield chart", "Show US Treasury 10Y yield chart"),
                    _shortcut_item("Web search", "Search for latest macro economic news"),
                    _shortcut_item("Latest news summary", "Summarize today's top macro news"),
                ]),
                # Reports (AlpaTrade-style expander)
                _expander_section("Reports", "reports", [
                    _shortcut_item("News history", "Show news history"),
                    _shortcut_item("Market movers today", "Show me top market movers"),
                    _shortcut_item("Event categories", "What macro event categories are active?"),
                ]),
                # Upcoming Events
                Div(
                    Div("Events", cls="sidebar-section-title"),
                    _upcoming_events_widget(),
                    cls="sidebar-section",
                ),
                # Event Categories (collapsible)
                _expander_section("Categories", "categories", [
                    *[_sidebar_category(cat, active=(cat["slug"] == active_category)) for cat in categories],
                ]),
                # News (collapsed)
                _expander_section("News", "news", [
                    A(DivLAligned(UkIcon("list", height=14, style="color:#94a3b8;"), Span("News History", style="font-size:0.8rem;"), cls="gap-2"),
                      href="/view/history", hx_get="/view/history", hx_target="#center-content", hx_swap="innerHTML",
                      cls="sidebar-topic no-underline"),
                    A(DivLAligned(UkIcon("rss", height=14, style="color:#94a3b8;"), Span("Live Feed", style="font-size:0.8rem;"), cls="gap-2"),
                      href="#", cls="sidebar-topic no-underline",
                      onclick="togglePane('right'); return false;"),
                ]),
                # Footer
                Div(
                    Span(f"v{APP_VERSION}", style="font-size:0.55rem; color:#475569;"),
                    cls="sidebar-footer",
                ),
                id="left-pane",
                cls="left-pane",
            ),

            # CENTER PANE
            Div(
                Div(*msg_bubbles, id="chat-messages", cls="feed-area"),
                Script("setTimeout(function(){var c=document.getElementById('chat-messages'); c.scrollTop=c.scrollHeight;},100);"),
                Div(
                    Form(
                        DivFullySpaced(
                            Input(name="msg", id="chat-input", placeholder="Ask about macro news, FX movements, central bank decisions...", autofocus=True, cls="uk-input uk-width-expand"),
                            Button(UkIcon("send", height=16), type="submit", cls=ButtonT.primary),
                            cls="gap-2",
                        ),
                        Input(name="website", type="text", tabindex="-1", autocomplete="off",
                              style="position:absolute;left:-9999px;width:1px;height:1px;opacity:0;"),
                        hx_post=f"/chat/{session_id}/send",
                        hx_target="#chat-messages",
                        hx_swap="beforeend",
                        hx_on__before_request="document.getElementById('chat-input').disabled=true;",
                        hx_on__after_request="this.reset(); setTimeout(function(){var c=document.getElementById('chat-messages'); c.scrollTop=c.scrollHeight;},200);",
                    ),
                    cls="chat-input-area",
                ),
                id="center-content",
                cls="center-pane",
            ),

            # RIGHT PANE
            Div(
                H4(DivLAligned(UkIcon("rss", height=16), Span("Macro News Feed", cls="text-sm font-semibold"), cls="gap-2"), cls="mb-2"),
                Div(
                    Div(
                        id="live-feed-items",
                        hx_ext="sse",
                        sse_connect="/sse/feed",
                        sse_swap="new-article",
                        hx_swap="afterbegin",
                    ),
                    *[MacroArticleCard(a) for a in recent_articles],
                    id="feed-scroll",
                    style="overflow-y: auto; max-height: calc(100vh - 120px);",
                ),
                id="right-pane",
                cls="right-pane",
            ),

            cls="app-layout",
        ),
    )


# ===================== STARTUP =====================

@app.on_event("startup")
async def startup():
    for cat in get_event_categories():
        category_queues[cat["slug"]] = asyncio.Queue()
    logger.info(f"Created {len(category_queues)} category queues")

    from services.feed_scheduler import run_feed_scheduler
    from services.daily_enrichment import run_daily_scheduler
    asyncio.create_task(run_feed_scheduler(config, shutdown_event, article_queue, category_queues))
    asyncio.create_task(run_daily_scheduler(shutdown_event))
    logger.info("Background schedulers started")


serve(port=config["app"].get("port", 5030))
