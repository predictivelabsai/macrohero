"""
MacroHero landing page — dark finance / macro intelligence register.

Public marketing site for the MacroHero macro-economic analysis platform.
Content adapted from macrohive.com, branded for MacroHero.

The renderer is exposed as `landing_page()` and called from main.py's `/`
route when no user is signed in.
"""

from fasthtml.common import (
    Html, Head, Body, Meta, Title, Link, Script, Style, NotStr,
    Nav, Main, Footer, Section, Article, Div, Span, A, P, H1, H2, H3, H4,
    Ul, Li, Img, Video, Source,
)


SITE_NAME = "MacroHero"
TAGLINE = "AI-powered macro intelligence for FX and rates trading."
CONTACT_EMAIL = "info@macrohero.com"


# MacroHero palette — white body, dark navy sidebar-matched hero,
# blue accent (#3b82f6), slate tones matching the app sidebar.
TAILWIND_CONFIG = """
tailwind.config = {
  theme: {
    extend: {
      colors: {
        bg:   { DEFAULT: '#FFFFFF', elevated: '#F8FAFC', raised: '#FFFFFF' },
        ink:  { DEFAULT: '#0f172a', muted: '#475569', dim: '#94a3b8' },
        line: { DEFAULT: '#e2e8f0', bright: '#cbd5e1' },
        accent: { DEFAULT: '#3b82f6', deep: '#2563eb', dim: '#dbeafe' },
        deep:   { DEFAULT: '#0f172a', alt: '#1e293b', soft: '#334155' },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'ui-monospace', 'monospace'],
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter: '-0.025em',
      },
    },
  },
};
"""

LANDING_CSS = """
.hero-bg {
  background: linear-gradient(180deg,
    #0f172a 0%,
    #1e293b 40%,
    #0f172a 100%);
}
.hero-grid {
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(59,130,246,0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(59,130,246,0.05) 1px, transparent 1px);
  background-size: 60px 60px;
  pointer-events: none;
}
.hero-glow {
  position: absolute;
  top: 30%;
  left: 50%;
  transform: translateX(-50%);
  width: 600px;
  height: 400px;
  background: radial-gradient(ellipse at center,
    rgba(59,130,246,0.15) 0%,
    rgba(59,130,246,0.05) 40%,
    transparent 70%);
  pointer-events: none;
}
.product-card { transition: transform 200ms ease, border-color 200ms ease; }
.product-card:hover { transform: translateY(-2px); border-color: #3b82f6; }
.team-photo {
  aspect-ratio: 1/1;
  width: 100%;
  object-fit: cover;
  background: #f1f5f9;
  display: block;
  filter: saturate(0.9);
}
.demo-video {
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.1);
  box-shadow: 0 25px 50px -12px rgba(0,0,0,0.4);
  max-width: 900px;
  width: 100%;
}
.stat-card {
  text-align: center;
  padding: 20px;
}
.feature-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(59,130,246,0.1);
  color: #3b82f6;
  font-size: 1.2rem;
  margin-bottom: 12px;
}
"""


# ---------------------------------------------------------------------------
# Atom components
# ---------------------------------------------------------------------------

def _eyebrow(text, *, on_dark=False):
    color = "text-accent" if not on_dark else "text-accent"
    return Span(text, cls=f"font-mono text-[11px] tracking-[0.18em] uppercase {color}")


def _heading(level, text, *, cls="", on_dark=False):
    tag = {1: H1, 2: H2, 3: H3, 4: H4}[level]
    base = {
        1: "text-4xl sm:text-5xl md:text-7xl font-medium tracking-tightest leading-[1.05] md:leading-[1.02]",
        2: "text-2xl sm:text-3xl md:text-5xl font-medium tracking-tighter leading-[1.12] md:leading-[1.08]",
        3: "text-lg sm:text-xl md:text-2xl font-medium tracking-tight",
        4: "text-base md:text-lg font-medium",
    }[level]
    color = "text-white" if on_dark else "text-ink"
    return tag(text, cls=f"{base} {color} {cls}".strip())


def _btn(text, *, href="#", primary=True, cls=""):
    base = "inline-flex items-center gap-2 px-5 py-3 text-sm font-medium tracking-wide uppercase transition-all duration-200"
    if primary:
        style = "bg-accent text-white hover:bg-accent-deep border border-accent rounded-lg"
    else:
        style = "bg-transparent text-ink border border-ink/30 hover:border-accent hover:text-accent rounded-lg"
    return A(text, Span("→", cls="text-base"), href=href, cls=f"{base} {style} {cls}".strip())


def _btn_on_dark(text, *, href="#", primary=True, cls=""):
    base = "inline-flex items-center gap-2 px-5 py-3 text-sm font-medium tracking-wide uppercase transition-all duration-200"
    if primary:
        style = "bg-accent text-white hover:bg-accent-deep border border-accent rounded-lg"
    else:
        style = "bg-transparent text-white border border-white/30 hover:border-accent hover:text-accent rounded-lg"
    return A(text, Span("→", cls="text-base"), href=href, cls=f"{base} {style} {cls}".strip())


# ---------------------------------------------------------------------------
# Navbar / Footer
# ---------------------------------------------------------------------------

NAV_ITEMS = [
    ("Features",     "#features"),
    ("How it works", "#how"),
    ("Team",         "#team"),
]


def _navbar():
    return Nav(
        Div(
            A(
                Span("↗", cls="text-accent mr-2 text-lg"),
                Span(SITE_NAME, cls="font-medium tracking-tight"),
                href="/",
                cls="flex items-center text-ink text-base hover:text-accent transition-colors",
            ),
            Ul(
                *[
                    Li(A(label, href=href, cls="text-sm text-ink-muted hover:text-ink transition-colors"))
                    for label, href in NAV_ITEMS
                ],
                cls="hidden lg:flex items-center gap-7",
            ),
            Div(
                A("Sign in", href="/login",
                  cls="text-sm text-ink-muted hover:text-ink transition-colors"),
                A("Book a demo", href="/register",
                  cls="inline-flex items-center gap-2 px-4 py-2 rounded-full text-xs font-medium bg-accent text-white hover:bg-accent-deep transition-colors"),
                cls="flex items-center gap-4",
            ),
            cls="max-w-7xl mx-auto px-5 md:px-6 flex items-center justify-between h-16 gap-4",
        ),
        cls="sticky top-0 z-50 backdrop-blur-md bg-bg/80 border-b border-line",
    )


def _footer():
    columns = [
        ("Platform", [
            ("Features", "#features"),
            ("How it works", "#how"),
            ("Sign in", "/login"),
        ]),
        ("Research", [
            ("FX Strategies", "#features"),
            ("Backtesting", "#features"),
            ("Market Movers", "#features"),
        ]),
        ("Company", [
            ("Team", "#team"),
            ("Book a demo", "/register"),
            ("Contact", f"mailto:{CONTACT_EMAIL}"),
        ]),
    ]
    return Footer(
        Div(
            Div(
                *[
                    Div(
                        H4(title, cls="text-xs font-mono tracking-widest uppercase text-ink-dim mb-4"),
                        Ul(
                            *[Li(A(label, href=href, cls="text-sm text-ink-muted hover:text-ink transition-colors"), cls="mb-2") for label, href in links],
                            cls="list-none p-0",
                        ),
                    )
                    for title, links in columns
                ],
                cls="grid grid-cols-2 md:grid-cols-3 gap-10",
            ),
            Div(
                Div(
                    A(
                        Span("↗", cls="text-accent mr-2"),
                        Span(SITE_NAME, cls="font-medium"),
                        href="/",
                        cls="flex items-center text-ink text-sm hover:text-accent transition-colors",
                    ),
                    P(f"© 2026 {SITE_NAME}. All rights reserved.", cls="text-xs text-ink-dim mt-1"),
                ),
                cls="mt-12 pt-6 border-t border-line flex items-center justify-between flex-wrap gap-4",
            ),
            cls="max-w-7xl mx-auto px-5 md:px-6",
        ),
        cls="py-14 md:py-20 bg-bg-elevated border-t border-line",
    )


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _hero():
    import os
    has_demo = os.path.exists("docs/demo_video.gif")

    demo_el = None
    if has_demo:
        demo_el = Div(
            Img(src="/static/demo_video.gif", alt="MacroHero Demo",
                cls="demo-video"),
            cls="mt-12 md:mt-16 flex justify-center",
        )

    return Section(
        Div(
            Div(cls="hero-grid"),
            Div(cls="hero-glow"),
            Div(
                _eyebrow(f"{SITE_NAME} · Macro Intelligence Platform", on_dark=True),
                H1(
                    Span("AI-powered "),
                    Span("macro intelligence", cls="text-accent"),
                    Span(" for FX and rates trading."),
                    cls="mt-5 md:mt-6 text-[40px] sm:text-5xl md:text-7xl lg:text-[78px] font-medium tracking-tightest text-white leading-[1.05] md:leading-[1.02] max-w-5xl",
                ),
                P(
                    f"{SITE_NAME} combines real-time macro news analysis, AI-driven FX strategy generation, and institutional-grade backtesting — giving traders and analysts the edge in an increasingly complex global macro landscape. ",
                    "Built by macro strategists and quant developers, inspired by ",
                    A("Macro Hive", href="https://macrohive.com", target="_blank", rel="noopener",
                      cls="underline decoration-accent/70 underline-offset-4 hover:decoration-accent text-white"),
                    ".",
                    cls="mt-6 md:mt-8 text-base md:text-xl text-white/80 max-w-2xl leading-relaxed",
                ),
                Div(
                    _btn_on_dark("Sign in", href="/login", primary=True),
                    _btn_on_dark("Book a demo", href="/register", primary=False),
                    cls="mt-8 md:mt-10 flex items-center gap-3 flex-wrap",
                ),
                demo_el if demo_el else None,
                cls="relative z-10 max-w-7xl mx-auto px-5 md:px-6 py-24 md:py-32",
            ),
            cls="relative min-h-[70vh] md:min-h-[80vh] flex items-center overflow-hidden hero-bg",
        ),
        Div(
            Div(
                Div("A macro intelligence operating system", cls="text-[11px] md:text-xs font-mono tracking-[0.18em] uppercase text-ink-dim"),
                Div(
                    Span("6 currency pairs · ", cls="text-ink-muted text-xs md:text-sm"),
                    Span("8 AI tools · ", cls="text-accent text-xs md:text-sm font-mono"),
                    Span("7 event categories · ", cls="text-ink-muted text-xs md:text-sm"),
                    Span("5 news sources", cls="text-ink-muted text-xs md:text-sm"),
                ),
                cls="max-w-7xl mx-auto px-5 md:px-6 py-4 md:py-5 flex items-center justify-between flex-wrap gap-3",
            ),
            cls="border-y border-line bg-bg-elevated/60",
        ),
    )


FEATURES = [
    ("01", "Agentic Chat", "chart-line",
     "Ask questions about macro events, FX movements, and central bank decisions. The AI agent searches the web, queries the news database, and generates structured analysis with strategy recommendations."),
    ("02", "FX Backtesting", "bar-chart-2",
     "Backtest momentum strategies on major currency pairs with configurable parameters — lookback period, take profit, stop loss. Get Sharpe ratio, max drawdown, equity curves, and full trade logs."),
    ("03", "Market Movers", "zap",
     "Real-time identification of the highest-impact macro news stories, ranked by predicted FX magnitude and direction. Track which events are moving markets right now."),
    ("04", "Treasury vs FX Charts", "trending-up",
     "Interactive dual-axis Plotly charts comparing US Treasury yields against FX pairs. Visualize the interest rate differential channel in real time."),
    ("05", "Live News Feed", "rss",
     "Continuous RSS ingestion from Financial Times, Bloomberg, Wall Street Journal, Reuters, and CNBC. AI-enriched with sentiment, currency tags, and predicted impact."),
    ("06", "Economic Calendar", "calendar",
     "Upcoming macro events from EODHD — central bank meetings, employment reports, GDP releases. Filtered by impact level and country."),
    ("07", "Strategy Agent", "cpu",
     "Specialized backtest strategy agent that designs optimal parameters based on macro regime classification — geopolitical shock, trending, range-bound, or high volatility."),
    ("08", "Event Categories", "layers",
     "Seven macro event categories — Central Bank, Earnings, GDP, Trade & Tariffs, Employment, Inflation, Geopolitical — each with keyword-based auto-classification."),
]


def _feature_card(num, title, icon, body):
    icon_symbols = {
        "chart-line": "📊", "bar-chart-2": "📈", "zap": "⚡",
        "trending-up": "📉", "rss": "📰", "calendar": "📅",
        "cpu": "🤖", "layers": "🗂️",
    }
    return Article(
        Div(
            Div(icon_symbols.get(icon, "◆"), cls="feature-icon"),
            Span(num, cls="font-mono text-xs tracking-widest text-ink-dim ml-auto"),
            cls="flex items-center mb-6",
        ),
        _heading(3, title, cls="mb-3"),
        P(body, cls="text-ink-muted text-sm leading-relaxed"),
        cls="product-card p-7 rounded-2xl bg-bg-elevated border border-line h-full",
    )


def _features_section():
    return Section(
        Div(
            Div(
                _eyebrow("Features"),
                _heading(2, "Eight tools, one macro intelligence platform.", cls="mt-4 max-w-3xl"),
                P(
                    "MacroHero is the workspace macro strategists, FX traders, and portfolio managers use to track global events, generate trade ideas, and backtest strategies — all powered by AI and real-time data.",
                    cls="mt-5 text-ink-muted text-lg max-w-3xl leading-relaxed",
                ),
                cls="mb-14",
            ),
            Div(
                *[_feature_card(n, t, i, b) for n, t, i, b in FEATURES],
                cls="grid md:grid-cols-2 lg:grid-cols-3 gap-5",
            ),
            cls="max-w-7xl mx-auto px-5 md:px-6",
        ),
        id="features",
        cls="py-14 md:py-20 lg:py-28 border-b border-line",
    )


def _how():
    steps = [
        ("01", "Ask a question",
         "Type a macro question or select a shortcut — 'FX strategies for a Hormuz deal', 'Backtest EUR/USD momentum', 'What's moving markets today'. The AI agent takes it from there."),
        ("02", "Get structured analysis",
         "MacroHero responds with a professional trading desk format: Macro Framework table, Strategy Breakdown with conviction levels, Summary Table, and actionable next steps tied to specific backtests."),
        ("03", "Backtest and iterate",
         "Click a backtest suggestion to run it instantly. Watch trades stream in live. Compare parameter sets. Refine your strategy with real historical data before committing capital."),
    ]
    return Section(
        Div(
            Div(
                _eyebrow("How it works"),
                _heading(2, "From macro question to backtest in three steps.", cls="mt-4 max-w-3xl"),
                cls="mb-14",
            ),
            Div(
                *[
                    Div(
                        Span(num, cls="font-mono text-4xl md:text-5xl text-accent/30 font-medium"),
                        _heading(3, title, cls="mt-3 mb-3"),
                        P(body, cls="text-ink-muted text-sm leading-relaxed"),
                        cls="",
                    )
                    for num, title, body in steps
                ],
                cls="grid md:grid-cols-3 gap-10",
            ),
            cls="max-w-7xl mx-auto px-5 md:px-6",
        ),
        id="how",
        cls="py-14 md:py-20 lg:py-28 border-b border-line bg-bg-elevated/40",
    )


def _product_tour():
    return Section(
        Div(
            Div(
                _eyebrow("Product tour"),
                _heading(2, "See it in motion.", cls="mt-3 max-w-3xl mb-2"),
                P(
                    "A 20-second walk through the platform — macro chat, live backtesting, "
                    "currency pairs, news history, and the dark-themed trading sidebar. "
                    "Built for traders who think in macro.",
                    cls="mt-2 text-ink-muted text-base max-w-2xl leading-relaxed mb-6",
                ),
                cls="mb-6",
            ),
            A(
                Img(
                    src="/static/demo_video.gif",
                    alt="MacroHero product tour — chat, backtesting, market analysis",
                    loading="lazy",
                    cls="block w-full h-auto rounded-2xl border border-line shadow-[0_8px_40px_rgba(0,0,0,0.06)]",
                ),
                href="/login",
                cls="block rounded-2xl overflow-hidden hover:opacity-95 transition-opacity",
                title="Sign in to MacroHero",
            ),
            Div(
                A(
                    Span("Sign in"), Span("→", cls="ml-1"),
                    href="/login",
                    cls="inline-flex items-center gap-2 text-sm text-accent hover:text-ink",
                ),
                Span("·", cls="text-ink-dim mx-3"),
                A(
                    Span("Book a demo"), Span("→", cls="ml-1"),
                    href="mailto:info@macrohero.com?subject=MacroHero Demo Request",
                    cls="inline-flex items-center gap-2 text-sm text-accent hover:text-ink",
                ),
                cls="mt-5 flex items-center flex-wrap gap-y-2",
            ),
            cls="max-w-7xl mx-auto px-5 md:px-6 py-14 md:py-20 border-t border-line",
        ),
        id="tour",
    )


STARTERS = [
    ("Give me FX strategies for a Hormuz deal scenario", "globe"),
    ("Backtest momentum on EUR/USD over last year", "bar-chart-2"),
    ("Short USD/JPY — backtest with 1% TP, 0.5% SL", "trending-up"),
    ("What's moving markets today?", "zap"),
    ("US Treasury vs EUR/USD chart", "landmark"),
    ("Show me top market movers", "activity"),
]


def _starter_cards_section():
    icon_map = {
        "globe": "🌍", "bar-chart-2": "📊", "trending-up": "📈",
        "zap": "⚡", "landmark": "🏛️", "activity": "📉",
    }
    return Section(
        Div(
            Div(
                _eyebrow("Try it"),
                _heading(2, "Start with a question.", cls="mt-4 max-w-3xl"),
                P(
                    "These are the same shortcut cards that appear in the MacroHero chat. Sign in and click any of them to get an instant macro analysis.",
                    cls="mt-5 text-ink-muted text-lg max-w-2xl leading-relaxed",
                ),
                cls="mb-14",
            ),
            Div(
                *[
                    A(
                        Article(
                            Div(
                                Span(icon_map.get(icon, "◆"), cls="text-xl mr-3"),
                                Span(question, cls="text-ink text-sm font-medium"),
                                cls="flex items-center",
                            ),
                            cls="product-card p-5 rounded-xl bg-bg-elevated border border-line",
                        ),
                        href="/login",
                        cls="block no-underline",
                    )
                    for question, icon in STARTERS
                ],
                cls="grid md:grid-cols-2 lg:grid-cols-3 gap-4",
            ),
            cls="max-w-7xl mx-auto px-5 md:px-6",
        ),
        cls="py-14 md:py-20 lg:py-28 border-b border-line",
    )


TEAM = [
    ("Bilal Hafeez", "Founder & CEO",
     "Ex-Global Head of Fixed Income Strategy at Nomura. Former Head of Multi-Asset Research at Deutsche Bank. Ranked #1 macro strategist by Institutional Investor."),
    ("Andrew Simon", "Co-founder",
     "Co-architect of the Macro Hive platform. Deep expertise in financial technology and macro research infrastructure."),
    ("Viresh Kanabar", "Investment Strategist",
     "8+ years investment experience. Ex-CCLA Investment Management, managing £12B in assets across macro and multi-asset strategies."),
    ("Neel Mehta", "Cross-Asset Strategist",
     "27 years at sell-side institutions. Cross-asset volatility and correlation specialist with deep FX options background."),
    ("Iain Wadie", "Senior Software Engineer",
     "M.Eng & PhD from University of Bristol, MIF from London Business School. Full-stack engineering for quantitative finance platforms."),
]


def _team_card(name, role, bio):
    initials = "".join(w[0] for w in name.split()[:2])
    return Article(
        Div(
            Span(initials, cls="text-2xl font-medium text-accent"),
            cls="team-photo rounded-xl border border-line flex items-center justify-center bg-bg-elevated",
        ),
        Div(
            H4(name, cls="text-ink text-base font-medium mt-4"),
            P(role, cls="text-accent text-xs font-mono mt-1 leading-snug"),
            P(bio, cls="text-ink-muted text-xs mt-2 leading-relaxed"),
            cls="px-1",
        ),
        cls="",
    )


def _team_section():
    return Section(
        Div(
            Div(
                _eyebrow("Team"),
                _heading(2, "Built by macro strategists and quant developers.", cls="mt-4 max-w-3xl"),
                P(
                    "The MacroHero team combines decades of institutional macro research, FX trading, and quantitative development experience. "
                    "Content and team adapted from ",
                    A("Macro Hive", href="https://macrohive.com/meet-the-team/", target="_blank", rel="noopener",
                      cls="text-ink underline decoration-accent/50 underline-offset-4 hover:text-accent"),
                    ".",
                    cls="mt-5 text-ink-muted text-lg max-w-3xl leading-relaxed",
                ),
                cls="mb-14",
            ),
            Div(
                *[_team_card(n, r, b) for n, r, b in TEAM],
                cls="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-6",
            ),
            cls="max-w-7xl mx-auto px-5 md:px-6",
        ),
        id="team",
        cls="py-14 md:py-20 lg:py-28 border-t border-line",
    )


def _cta():
    return Section(
        Div(
            Div(cls="hero-grid"),
            Div(cls="hero-glow"),
            Div(
                _heading(2, "Ready to trade smarter?", cls="text-center", on_dark=True),
                P(
                    "Join macro strategists and FX traders using MacroHero to generate trade ideas, backtest strategies, and stay ahead of market-moving events.",
                    cls="mt-5 text-white/80 text-lg max-w-2xl mx-auto text-center leading-relaxed",
                ),
                Div(
                    _btn_on_dark("Sign in", href="/login", primary=True),
                    _btn_on_dark("Book a demo", href="/register", primary=False),
                    cls="mt-8 flex items-center justify-center gap-3 flex-wrap",
                ),
                cls="relative z-10 max-w-7xl mx-auto px-5 md:px-6 py-20 md:py-28 text-center",
            ),
            cls="relative overflow-hidden hero-bg",
        ),
    )


# ---------------------------------------------------------------------------
# Page assembly
# ---------------------------------------------------------------------------

def landing_page():
    head_children = [
        Meta(charset="utf-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1"),
        Meta(name="description", content=TAGLINE),
        Title(f"{SITE_NAME} — {TAGLINE}"),
        Link(rel="icon", type="image/svg+xml", href="/static/favicon.svg"),
        Link(rel="preconnect", href="https://fonts.googleapis.com"),
        Link(rel="preconnect", href="https://fonts.gstatic.com", crossorigin=""),
        Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap",
        ),
        Script(src="https://cdn.tailwindcss.com"),
        Script(NotStr(TAILWIND_CONFIG)),
        Style(LANDING_CSS),
    ]
    body_children = [
        _navbar(),
        Main(
            _hero(),
            _features_section(),
            _how(),
            _product_tour(),
            _starter_cards_section(),
            _team_section(),
            _cta(),
            cls="min-h-screen",
        ),
        _footer(),
    ]
    return Html(
        Head(*head_children),
        Body(*body_children, cls="bg-bg text-ink font-sans antialiased"),
        lang="en",
    )
