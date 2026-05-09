import os
import json
import logging
import markdown
from typing import AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from db.pool import fetch_all
from utils.config import load_config

logger = logging.getLogger(__name__)

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        config = load_config()
        _llm = ChatOpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1",
            model=config["llm"]["model"],
            temperature=config["llm"]["temperature"],
            max_tokens=config["llm"]["max_tokens"],
            streaming=True,
        )
    return _llm


@tool
def search_tavily(query: str) -> str:
    """Search the web for recent macro-economic news using Tavily. Use this for breaking news, central bank decisions, or economic data releases."""
    import asyncio
    from services.search_service import search_tavily as _search
    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            results = pool.submit(asyncio.run, _search(query, 5)).result()
    except Exception as e:
        return f"Search failed: {e}"
    if not results:
        return "No results found."
    lines = []
    for r in results:
        lines.append(f"- [{r['title']}]({r['url']})\n  {r['summary'][:200]}")
    return "\n".join(lines)


@tool
def get_recent_macro_news(category: str = "", limit: int = 10) -> str:
    """Get recent macro news from the MacroHero database, optionally filtered by event category slug (central-bank, earnings, gdp, trade, employment, inflation, geopolitical)."""
    if category:
        articles = fetch_all("""
            SELECT n.title, n.url, n.region, n.currency_tag, n.event_category,
                   n.predicted_direction, n.predicted_magnitude, n.market_reasoning,
                   s.name AS source_name
            FROM macro_news n
            LEFT JOIN sources s ON s.id = n.source_id
            JOIN news_categories nc ON nc.news_id = n.id
            JOIN event_categories c ON c.id = nc.category_id AND c.slug = :slug
            ORDER BY n.created_at DESC LIMIT :limit
        """, {"slug": category, "limit": limit})
    else:
        articles = fetch_all("""
            SELECT n.title, n.url, n.region, n.currency_tag, n.event_category,
                   n.predicted_direction, n.predicted_magnitude, n.market_reasoning,
                   s.name AS source_name
            FROM macro_news n
            LEFT JOIN sources s ON s.id = n.source_id
            ORDER BY n.created_at DESC LIMIT :limit
        """, {"limit": limit})
    if not articles:
        return "No articles found."
    lines = []
    for a in articles:
        direction = a.get("predicted_direction", "")
        mag = a.get("predicted_magnitude")
        move = f" [{direction} {mag:+.2f}%]" if direction and mag else ""
        currency = f" ({a['currency_tag']})" if a.get("currency_tag") else ""
        src = f" - {a['source_name']}" if a.get("source_name") else ""
        lines.append(f"- {a['title']}{src}{currency}{move}\n  URL: {a['url']}")
    return "\n".join(lines)


@tool
def analyze_currency_pair(pair: str, period: str = "5d") -> str:
    """Get live FX rate data for a currency pair using yfinance. Pair format: EURUSD, GBPUSD, USDJPY, etc. Period: 1d, 5d, 1mo, 3mo."""
    import yfinance as yf
    ticker = f"{pair.upper()}=X"
    try:
        data = yf.Ticker(ticker).history(period=period)
        if data.empty:
            return f"No data found for {pair}"
        latest = data.iloc[-1]
        first = data.iloc[0]
        change = latest["Close"] - first["Close"]
        change_pct = (change / first["Close"]) * 100
        lines = [
            f"**{pair.upper()}** ({period})",
            f"Current: {latest['Close']:.4f}",
            f"Open ({period} ago): {first['Close']:.4f}",
            f"Change: {change:+.4f} ({change_pct:+.2f}%)",
            f"Period High: {data['High'].max():.4f}",
            f"Period Low: {data['Low'].min():.4f}",
        ]
        return "\n".join(lines)
    except Exception as e:
        return f"Error fetching {pair}: {e}"


@tool
def get_market_movers(hours: int = 24) -> str:
    """Get the top market-moving macro news from the last N hours, ranked by predicted FX impact magnitude."""
    articles = fetch_all("""
        SELECT n.title, n.url, n.currency_tag, n.predicted_direction,
               n.predicted_magnitude, n.market_reasoning, s.name AS source_name
        FROM macro_news n
        LEFT JOIN sources s ON s.id = n.source_id
        WHERE n.created_at > NOW() - make_interval(hours => :hours)
          AND n.predicted_magnitude IS NOT NULL
        ORDER BY ABS(n.predicted_magnitude) DESC LIMIT 10
    """, {"hours": hours})
    if not articles:
        return "No market movers found in the specified period."
    lines = []
    for a in articles:
        direction = a.get("predicted_direction", "")
        mag = a.get("predicted_magnitude", 0)
        currency = a.get("currency_tag", "")
        src = a.get("source_name", "")
        lines.append(f"- **{direction.upper()} {mag:+.2f}% {currency}** {a['title']} ({src})\n  {a.get('market_reasoning', '')[:150]}\n  URL: {a['url']}")
    return "\n".join(lines)


@tool
def get_treasury_vs_fx_chart(fx_pair: str = "EURUSD", period: str = "1y") -> str:
    """Generate a dual-axis chart comparing US Treasury 10Y yield vs an FX pair over time. Returns HTML with an interactive Plotly chart. Use this when the user asks to compare treasuries/interest rates with FX rates."""
    import asyncio
    from services.market_data_service import get_treasury_yields_multi_year, get_fx_history, build_dual_axis_chart_html

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            years = 2 if period in ("2y", "3y", "5y") else 1
            treasury_data = pool.submit(asyncio.run, get_treasury_yields_multi_year(years)).result()
            fx_data = pool.submit(asyncio.run, get_fx_history(fx_pair, period)).result()
    except Exception as e:
        return f"Error fetching data: {e}"

    if not treasury_data:
        return "No treasury yield data available from EODHD."
    if not fx_data.get("dates"):
        return f"No FX data available for {fx_pair}."

    t_dates = []
    t_yields = []
    for row in treasury_data:
        d = row.get("date") or row.get("Date") or ""
        y10 = row.get("10 Yr") or row.get("10Yr") or row.get("d10") or None
        if d and y10 is not None:
            t_dates.append(d)
            try:
                t_yields.append(float(y10))
            except (ValueError, TypeError):
                continue

    fx_dates = fx_data["dates"]
    fx_rates = fx_data["rates"]

    common_start = max(t_dates[0] if t_dates else "", fx_dates[0] if fx_dates else "")
    t_filtered = [(d, y) for d, y in zip(t_dates, t_yields) if d >= common_start]
    fx_filtered = [(d, r) for d, r in zip(fx_dates, fx_rates) if d >= common_start]

    if not t_filtered or not fx_filtered:
        return "Not enough overlapping data to build chart."

    all_dates = sorted(set(d for d, _ in t_filtered) | set(d for d, _ in fx_filtered))
    t_map = dict(t_filtered)
    fx_map = dict(fx_filtered)

    chart_dates = []
    chart_t = []
    chart_fx = []
    last_t = t_filtered[0][1]
    last_fx = fx_filtered[0][1]
    for d in all_dates:
        chart_dates.append(d)
        last_t = t_map.get(d, last_t)
        last_fx = fx_map.get(d, last_fx)
        chart_t.append(last_t)
        chart_fx.append(last_fx)

    html = build_dual_axis_chart_html(
        title=f"US 10Y Treasury vs {fx_pair.upper()} ({period})",
        dates=chart_dates,
        series1_values=chart_t,
        series1_name="US 10Y Yield (%)",
        series2_values=chart_fx,
        series2_name=fx_pair.upper(),
        y1_label="Yield (%)",
        y2_label=fx_pair.upper(),
    )
    return f"CHART_HTML:{html}"


@tool
def get_fx_chart(pair: str = "EURUSD", period: str = "1y") -> str:
    """Generate a line chart for an FX currency pair over time. Returns HTML with an interactive Plotly chart."""
    import asyncio
    from services.market_data_service import get_fx_history, build_line_chart_html

    try:
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            fx_data = pool.submit(asyncio.run, get_fx_history(pair, period)).result()
    except Exception as e:
        return f"Error fetching data: {e}"

    if not fx_data.get("dates"):
        return f"No FX data available for {pair}."

    html = build_line_chart_html(
        title=f"{pair.upper()} ({period})",
        dates=fx_data["dates"],
        values=fx_data["rates"],
        series_name=pair.upper(),
        y_label="Rate",
        color="#3b82f6",
    )
    return f"CHART_HTML:{html}"


@tool
def get_treasury_chart(period: str = "1y") -> str:
    """Generate a line chart of US Treasury 10Y yield over time. Returns HTML with an interactive Plotly chart."""
    import asyncio
    from services.market_data_service import get_treasury_yields_multi_year, build_line_chart_html

    try:
        import concurrent.futures
        years = 2 if period in ("2y", "3y", "5y") else 1
        with concurrent.futures.ThreadPoolExecutor() as pool:
            data = pool.submit(asyncio.run, get_treasury_yields_multi_year(years)).result()
    except Exception as e:
        return f"Error fetching data: {e}"

    if not data:
        return "No treasury yield data available."

    dates = []
    yields_10y = []
    for row in data:
        d = row.get("date") or row.get("Date") or ""
        y10 = row.get("10 Yr") or row.get("10Yr") or row.get("d10") or None
        if d and y10 is not None:
            try:
                dates.append(d)
                yields_10y.append(float(y10))
            except (ValueError, TypeError):
                continue

    if not dates:
        return "No valid yield data found."

    html = build_line_chart_html(
        title=f"US Treasury 10Y Yield ({period})",
        dates=dates,
        values=yields_10y,
        series_name="10Y Yield",
        y_label="Yield (%)",
        color="#ef4444",
    )
    return f"CHART_HTML:{html}"


@tool
def backtest_fx_strategy(pair: str = "EURUSD", period: str = "1y", strategy: str = "momentum",
                         lookback: int = 20, take_profit: float = 1.0, stop_loss: float = 0.5) -> str:
    """Backtest an FX trading strategy on a currency pair. Returns metrics (Sharpe, return, drawdown), equity curve chart, and trade log.
    Use this when the user asks to backtest, test a strategy, or wants to see historical performance of an FX trade idea.
    Strategies: momentum (trend-following). Pair format: EURUSD, GBPUSD, USDJPY, etc."""
    from services.backtest_service import run_momentum_backtest, build_backtest_results_html
    try:
        result = run_momentum_backtest(
            pair=pair, period=period, lookback=lookback,
            take_profit=take_profit, stop_loss=stop_loss,
        )
        if "error" in result:
            return result["error"]
        return build_backtest_results_html(result)
    except Exception as e:
        return f"Backtest error: {e}"


TOOLS = [search_tavily, get_recent_macro_news, analyze_currency_pair, get_market_movers,
         get_treasury_vs_fx_chart, get_fx_chart, get_treasury_chart, backtest_fx_strategy]
TOOL_MAP = {t.name: t for t in TOOLS}
TOOL_LABELS = {
    "search_tavily": "Searching Tavily...",
    "get_recent_macro_news": "Checking macro news...",
    "analyze_currency_pair": "Fetching FX data...",
    "get_market_movers": "Finding market movers...",
    "get_treasury_vs_fx_chart": "Building Treasury vs FX chart...",
    "get_fx_chart": "Building FX chart...",
    "get_treasury_chart": "Building Treasury yield chart...",
    "backtest_fx_strategy": "Running FX backtest...",
}


def _get_context(category_slug: str = None) -> str:
    if category_slug:
        articles = fetch_all("""
            SELECT n.title, n.region, n.currency_tag, n.predicted_direction, n.predicted_magnitude
            FROM macro_news n
            JOIN news_categories nc ON nc.news_id = n.id
            JOIN event_categories c ON c.id = nc.category_id AND c.slug = :slug
            ORDER BY n.created_at DESC LIMIT 10
        """, {"slug": category_slug})
    else:
        articles = fetch_all("""
            SELECT n.title, n.region, n.currency_tag, n.predicted_direction, n.predicted_magnitude
            FROM macro_news n ORDER BY n.created_at DESC LIMIT 10
        """)
    if not articles:
        return "No recent articles."
    lines = []
    for a in articles:
        d = a.get("predicted_direction", "")
        m = a.get("predicted_magnitude")
        move = f" [{d} {m:+.2f}%]" if d and m else ""
        c = f" ({a['currency_tag']})" if a.get("currency_tag") else ""
        lines.append(f"- {a['title']}{c}{move}")
    return "\n".join(lines)


def _build_messages(chat_history: list[dict], category_slug: str = None) -> list:
    context = _get_context(category_slug)
    system_msg = f"""You are MacroHero, an AI macro-economic market analyst and trading strategist. You help users develop FX and interest rate trading strategies based on macro news, geopolitical events, and economic data.

TOOLS — use them aggressively:
- search_tavily: Search the web for breaking macro news, central bank decisions, economic data.
- get_recent_macro_news: Query the MacroHero database by event category (central-bank, earnings, gdp, trade, employment, inflation, geopolitical).
- analyze_currency_pair: Get live FX data from yfinance (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD).
- get_market_movers: Get top market-moving news ranked by predicted FX impact.
- get_treasury_vs_fx_chart: Generate a dual-axis Plotly chart comparing US 10Y Treasury yield vs an FX pair.
- get_fx_chart: Generate a Plotly line chart for an FX pair over time.
- get_treasury_chart: Generate a Plotly line chart of US 10Y Treasury yield over time.
- backtest_fx_strategy: Backtest an FX trading strategy on historical data. Returns metrics (Sharpe, return, drawdown), equity curve, and trade log.

RESPONSE FORMAT — ALWAYS structure your responses like a professional trading desk:

1. **Macro Framework**: Start with a markdown table summarizing the macro thesis (channels and implications).

2. **Strategy Breakdown**: For each strategy, use:
   - A ### header with the trade name and conviction level
   - Bullet points for rationale
   - Bold the specific **Trade:** expression (e.g., **Short USD/JPY**)

3. **Summary Table**: Include a ranked markdown table of strategies with columns: Rank, Trade, Rationale, Conviction.

4. **Next Steps**: ALWAYS end with "Would you like me to:" followed by 2-4 actionable backtest suggestions referencing the SPECIFIC strategies you just recommended. For example if you recommended Long EUR/USD and Short USD/CAD, suggest:
   - **Backtest Long EUR/USD** momentum strategy over last year?
   - **Backtest Short USD/CAD** with 1% TP, 0.5% SL?
   - **Show Treasury vs EUR/USD** correlation chart?
   Do NOT suggest generic technical analysis. Every suggestion should be a concrete, executable action tied to the strategies above.

STRATEGY:
1. For scenario/thesis questions (e.g., "strategies for a Hormuz deal"): Build a complete macro framework with FX + IR strategies, ranked summary table, and backtest suggestions.
2. For backtest requests: use backtest_fx_strategy. The tool returns CHART_HTML — include it verbatim.
3. For chart/visualization requests: use chart tools. When the tool returns CHART_HTML, include it verbatim.
4. For currency pair questions: use BOTH analyze_currency_pair AND get_recent_macro_news.
5. For broad questions ("what's moving markets"): use get_market_movers first.
6. Always include source, region, currency, and predicted direction/magnitude when available.

Format: Use markdown tables (|col1|col2|), headers (##, ###), bold (**text**), bullet lists. Use [title](url) for links.
When a tool returns text starting with CHART_HTML:, include the HTML after CHART_HTML: as-is in your response — the frontend renders it.

RECENT MACRO NEWS IN DATABASE:
{context}"""

    messages = [SystemMessage(content=system_msg)]
    for msg in chat_history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))
    return messages


def md_to_html(text: str) -> str:
    return markdown.markdown(text, extensions=["extra", "nl2br", "sane_lists"])


async def _run_streaming_backtest(args: dict) -> AsyncGenerator[dict, None]:
    """Run backtest yielding streaming events + final result."""
    from services.backtest_service import (
        run_momentum_backtest_streaming, build_backtest_results_html,
        build_streaming_header_html, build_trade_row_html,
    )
    pair = args.get("pair", "EURUSD")
    period = args.get("period", "1y")
    lookback = args.get("lookback", 20)
    take_profit = args.get("take_profit", 1.0)
    stop_loss = args.get("stop_loss", 0.5)

    yield {"type": "backtest_header", "html": build_streaming_header_html(pair, "momentum")}

    import asyncio
    final_result = None
    try:
        for event in run_momentum_backtest_streaming(
            pair=pair, period=period, lookback=lookback,
            take_profit=take_profit, stop_loss=stop_loss,
        ):
            if event["type"] == "trade":
                yield {"type": "backtest_trade", "html": build_trade_row_html(event["trade"], event["index"])}
                await asyncio.sleep(0)
            elif event["type"] == "error":
                yield {"type": "backtest_result", "text": event["error"]}
                return
            elif event["type"] == "complete":
                final_result = event["result"]
    except Exception as e:
        yield {"type": "backtest_result", "text": f"Backtest error: {e}"}
        return

    if final_result:
        yield {"type": "backtest_result", "text": build_backtest_results_html(final_result)}
    else:
        yield {"type": "backtest_result", "text": "Backtest completed with no results."}


async def get_chat_response_stream(
    chat_history: list[dict],
    category_slug: str = None,
) -> AsyncGenerator[dict, None]:
    llm = _get_llm()
    llm_with_tools = llm.bind_tools(TOOLS)
    messages = _build_messages(chat_history, category_slug)

    yield {"type": "status", "text": "Thinking..."}

    full_text = ""
    tool_calls = []

    try:
        async for chunk in llm_with_tools.astream(messages):
            if chunk.content:
                full_text += chunk.content
            if hasattr(chunk, "tool_calls") and chunk.tool_calls:
                tool_calls.extend(chunk.tool_calls)
            if hasattr(chunk, "additional_kwargs"):
                tc = chunk.additional_kwargs.get("tool_calls", [])
                for t in tc:
                    if t.get("function", {}).get("name"):
                        tool_calls.append({
                            "id": t.get("id", ""),
                            "name": t["function"]["name"],
                            "args": t["function"].get("arguments", "{}"),
                        })
    except Exception as e:
        logger.error(f"Chat stream error: {e}")
        yield {"type": "token", "html": f'<p class="text-red-500">Error: {e}</p>'}
        return

    if tool_calls:
        seen = set()
        unique_calls = []
        for tc in tool_calls:
            name = tc.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique_calls.append(tc)

        assistant_msg = AIMessage(content=full_text, tool_calls=[
            {"id": tc.get("id", f"call_{i}"), "name": tc["name"], "args": json.loads(tc["args"]) if isinstance(tc.get("args"), str) else tc.get("args", {})}
            for i, tc in enumerate(unique_calls)
        ])
        messages.append(assistant_msg)

        for tc in unique_calls:
            name = tc.get("name", "")
            label = TOOL_LABELS.get(name, f"Using {name}...")
            yield {"type": "status", "text": label}

            if name == "backtest_fx_strategy":
                args = tc.get("args", {})
                if isinstance(args, str):
                    args = json.loads(args)
                result = ""
                async for bt_event in _run_streaming_backtest(args):
                    if bt_event["type"] == "backtest_result":
                        result = bt_event["text"]
                    else:
                        yield bt_event
            else:
                tool_fn = TOOL_MAP.get(name)
                if tool_fn:
                    try:
                        args = tc.get("args", {})
                        if isinstance(args, str):
                            args = json.loads(args)
                        result = tool_fn.invoke(args)
                    except Exception as e:
                        result = f"Tool error: {e}"
                else:
                    result = f"Unknown tool: {name}"

            call_id = tc.get("id", f"call_{unique_calls.index(tc)}")
            messages.append(ToolMessage(content=str(result), tool_call_id=call_id))

        yield {"type": "status", "text": "Composing response..."}
        full_text = ""
        for attempt in range(2):
            try:
                async for chunk in llm.astream(messages):
                    if chunk.content:
                        full_text += chunk.content
                if full_text:
                    break
                logger.warning(f"Empty response on attempt {attempt+1}, retrying...")
                messages.append(HumanMessage(content="Please provide your analysis based on the tool results above."))
                yield {"type": "status", "text": "Retrying..."}
            except Exception as e:
                logger.error(f"LLM call error (attempt {attempt+1}): {e}")
                if attempt == 1:
                    yield {"type": "token", "html": f'<p class="text-red-500">Error: {e}</p>'}
                    return

    # Check if any tool returned chart HTML
    chart_parts = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and msg.content.startswith("CHART_HTML:"):
            chart_parts.append(msg.content[len("CHART_HTML:"):])

    if full_text:
        # If the LLM included CHART_HTML in its response, extract and render
        if "CHART_HTML:" in full_text:
            parts = full_text.split("CHART_HTML:")
            md_part = parts[0].strip()
            chart_part = parts[1].strip() if len(parts) > 1 else ""
            html = md_to_html(md_part) if md_part else ""
            html += chart_part
        else:
            html = md_to_html(full_text)
        # Append any chart HTML from tool results that the LLM may have summarized
        if chart_parts:
            html += "\n" + "\n".join(chart_parts)
        yield {"type": "token", "html": html}
    elif chart_parts:
        yield {"type": "token", "html": "\n".join(chart_parts)}
    else:
        fallback_parts = []
        for msg in messages:
            if isinstance(msg, ToolMessage):
                fallback_parts.append(msg.content)
        if fallback_parts:
            yield {"type": "token", "html": md_to_html("\n\n".join(fallback_parts))}
        else:
            yield {"type": "token", "html": "<p style='color:#6b7280;'>No results found. Try rephrasing your question.</p>"}
