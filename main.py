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

app, rt = fast_app(
    hdrs=(
        Theme.blue.headers(highlightjs=True),
        sse_script,
        Style("""
            html, body { overflow-x: hidden; max-width: 100vw; }
            .app-layout { display: flex; gap: 0; height: calc(100vh - 60px); overflow: hidden; }
            .left-pane { width: 240px; min-width: 240px; overflow-y: auto; padding: 12px; border-right: 1px solid #e5e7eb; }
            .center-pane { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
            .right-pane { width: 380px; min-width: 380px; overflow-y: auto; padding: 12px; border-left: 1px solid #e5e7eb; }

            .feed-area { flex: 1; overflow-y: auto; padding: 16px; }
            .chat-input-area { padding: 12px 16px; border-top: 1px solid #e5e7eb; }

            #chat-messages { overflow-y: auto; padding: 0 16px; }
            #chat-messages:empty { display: none; }

            .sidebar-topic { cursor: pointer; padding: 8px 10px; border-radius: 8px; border-left: 3px solid transparent;
                             transition: background 0.15s, border-color 0.15s; margin-bottom: 4px; }
            .sidebar-topic:hover { background: #f3f4f6; }
            .sidebar-topic.active { background: #eff6ff; border-left-color: #3b82f6; }

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

            .app-nav { display: flex; align-items: center; justify-content: space-between; padding: 10px 20px; border-bottom: 1px solid #e5e7eb; height: 56px; }

            .sidebar-section { margin-bottom: 16px; }
            .sidebar-section-title { font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: #9ca3af; margin-bottom: 6px; padding-left: 10px; }

            .starter-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 12px; }
            .starter-card { cursor: pointer; padding: 10px 12px; border: 1px solid #e5e7eb; border-radius: 10px;
                            font-size: 0.8rem; transition: background 0.15s, border-color 0.15s; }
            .starter-card:hover { background: #eff6ff; border-color: #3b82f6; }

            .mobile-tabs { display: none; }
            @media (max-width: 768px) {
                .left-pane { display: none; position: fixed; top: 56px; left: 0; bottom: 0; z-index: 50; background: white; width: 85vw; box-shadow: 2px 0 12px rgba(0,0,0,0.15); }
                .left-pane.mobile-open { display: block; }
                .right-pane { display: none; position: fixed; top: 56px; right: 0; bottom: 0; z-index: 50; background: white; width: 85vw; box-shadow: -2px 0 12px rgba(0,0,0,0.15); }
                .right-pane.mobile-open { display: block; }
                .mobile-tabs { display: flex; justify-content: space-around; border-bottom: 1px solid #e5e7eb; padding: 6px 0; }
                .mobile-tabs button { background: none; border: none; font-size: 0.75rem; padding: 4px 12px; cursor: pointer; color: #6b7280; }
                .mobile-tabs button:hover { color: #1e40af; }
                .mobile-overlay { display: none; position: fixed; inset: 0; z-index: 40; background: rgba(0,0,0,0.3); }
                .mobile-overlay.active { display: block; }
                .app-layout { height: calc(100vh - 56px); }
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


def _create_new_session(category_slug: str = None) -> dict:
    result = fetch_one("""
        INSERT INTO chat_sessions (category_slug) VALUES (:slug) RETURNING id, category_slug, title, created_at
    """, {"slug": category_slug})
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


def _chat_history_items(active_session_id: str) -> list:
    sessions = fetch_all("""
        SELECT id, title, created_at FROM chat_sessions
        ORDER BY updated_at DESC LIMIT 8
    """)
    items = []
    for s in sessions:
        is_active = str(s["id"]) == active_session_id
        ts = s["created_at"].strftime("%H:%M") if hasattr(s["created_at"], "strftime") else ""
        title = s["title"][:22] + ("..." if len(s["title"]) > 22 else "")
        items.append(
            A(
                DivFullySpaced(
                    DivLAligned(UkIcon("message-circle", height=10), Span(title, cls="text-xs"), cls="gap-1"),
                    Span(ts, style="font-size:0.55rem; color:#9ca3af;"),
                ),
                href=f"/session/{s['id']}",
                cls="no-underline block py-1 px-2 rounded text-xs" + (" bg-primary/10" if is_active else " hover:bg-muted/50"),
            )
        )
    return items


def _sidebar_category(cat: dict, active: bool = False):
    count = cat.get("article_count", 0)
    return A(
        DivLAligned(
            UkIcon(cat["icon"], height=18),
            Div(
                Span(cat["name"], cls="text-sm font-medium"),
                Span(f" ({count})", cls="text-xs text-muted"),
            ),
            cls="gap-2",
        ),
        href=f"/category/{cat['slug']}",
        cls="sidebar-topic no-underline" + (" active" if active else ""),
        style=f"border-left-color: {cat['color']};" if active else "",
    )


def _starter_cards(session_id: str):
    starters = [
        ("What's moving markets today?", "trending-up"),
        ("EUR/USD outlook this week", "bar-chart-2"),
        ("Latest central bank news", "landmark"),
        ("Show me top market movers", "zap"),
        ("Trade & tariff impact on FX", "globe"),
        ("Employment data trends", "users"),
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


def _trending_widget(categories: list[dict]):
    if not categories:
        return P("No trending categories.", cls="text-xs text-muted px-2")
    items = []
    for cat in categories[:5]:
        items.append(
            DivFullySpaced(
                DivLAligned(
                    Span("", style=f"width:8px;height:8px;border-radius:50%;background:{cat['color']};display:inline-block;"),
                    Span(cat["name"], cls="text-xs"),
                    cls="gap-2",
                ),
                Span(str(cat.get("article_count", 0)), cls="text-xs text-muted"),
                cls="py-0.5",
            )
        )
    return Div(*items, id="trending-list",
               hx_get="/api/trending", hx_trigger="every 60s", hx_swap="outerHTML")


def _get_trending() -> list[dict]:
    return fetch_all("""
        SELECT c.name, c.slug, c.color, c.icon, COUNT(nc.news_id) AS article_count
        FROM event_categories c
        JOIN news_categories nc ON nc.category_id = c.id
        JOIN macro_news n ON n.id = nc.news_id
        WHERE n.created_at > NOW() - INTERVAL '24 hours'
        GROUP BY c.id, c.name, c.slug, c.color, c.icon
        ORDER BY article_count DESC
    """)


# ===================== ROUTES =====================

@rt
def index(req, sess):
    user = _get_session_user(sess)
    chat_sess = _create_new_session("general")
    return _app_shell(chat_sess, user=user)


@rt("/category/{category_slug}")
def category_view(category_slug: str, sess):
    user = _get_session_user(sess)
    chat_sess = _create_new_session(category_slug)
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


@rt("/api/trending")
def api_trending():
    return _trending_widget(_get_trending())


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
    try:
        async for event in get_chat_response_stream(messages, category_slug):
            if event["type"] == "status":
                yield sse_message(
                    Script(f"document.getElementById('thinking-text').textContent='{event['text']}';"),
                    event="token",
                )
            elif event["type"] == "token":
                html = event["html"]
                full_response = html
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
    return RedirectResponse("/", status_code=303)


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
    return RedirectResponse("/", status_code=303)


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
                Div(
                    P("Welcome to MacroHero!", cls="font-semibold text-sm"),
                    P("I'm your macro-economic market analyst. Ask me about central bank decisions, FX movements, trade policy, or any market-moving event. I can search the web and analyze live currency data.", cls="text-sm text-muted mt-1"),
                    _starter_cards(session_id),
                    cls="p-3",
                ),
                cls="chat-assistant",
            )
        )

    return (
        Title("MacroHero"),
        NavBar_(user),
        Div(
            Button(UkIcon("menu", height=14), " Categories", onclick="togglePane('left')", cls="text-xs"),
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
                Div(
                    DivFullySpaced(
                        A(
                            DivLAligned(UkIcon("plus", height=14), Span("New Chat", cls="text-xs font-medium"), cls="gap-1"),
                            href="/", cls="sidebar-topic no-underline", style="border: 1px dashed #d1d5db; border-left: none; flex:1;",
                        ),
                        Button(UkIcon("trash-2", height=12), cls="uk-button uk-button-default uk-button-small",
                               style="padding:2px 6px;", title="Clear history",
                               hx_post="/api/clear-history", hx_target="body", hx_confirm="Clear all chat history?"),
                        cls="gap-2 mb-1",
                    ),
                    *_chat_history_items(session_id),
                    cls="sidebar-section",
                ),
                # Market Views
                Div(
                    Div("Views", cls="sidebar-section-title"),
                    A(
                        DivLAligned(UkIcon("zap", height=18), Span("Market Movers", cls="text-sm font-medium"), cls="gap-2"),
                        href="#",
                        cls="sidebar-topic no-underline",
                        onclick="var inp=document.getElementById('chat-input'); inp.value='Show me top market movers'; inp.disabled=false; inp.form.requestSubmit(); return false;",
                    ),
                    A(
                        DivLAligned(UkIcon("bar-chart-2", height=18), Span("Currency Pairs", cls="text-sm font-medium"), cls="gap-2"),
                        href="/view/pairs", hx_get="/view/pairs", hx_target="#center-content", hx_swap="innerHTML",
                        cls="sidebar-topic no-underline",
                    ),
                    A(
                        DivLAligned(UkIcon("list", height=18), Span("News History", cls="text-sm font-medium"), cls="gap-2"),
                        href="/view/history", hx_get="/view/history", hx_target="#center-content", hx_swap="innerHTML",
                        cls="sidebar-topic no-underline",
                    ),
                    cls="sidebar-section",
                ),
                # Event Categories
                Div(
                    Div("Event Categories", cls="sidebar-section-title"),
                    *[_sidebar_category(cat, active=(cat["slug"] == active_category)) for cat in categories],
                    cls="sidebar-section",
                ),
                # Trending
                Div(
                    Div("Trending", cls="sidebar-section-title"),
                    _trending_widget(_get_trending()),
                    cls="sidebar-section",
                ),
                # Version
                Div(
                    Span(f"v{APP_VERSION}", style="font-size:0.55rem; color:#c0c0c0;"),
                    style="padding:8px 10px; margin-top:auto;",
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
