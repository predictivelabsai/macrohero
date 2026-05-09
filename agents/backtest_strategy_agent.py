import os
import json
import logging
from typing import AsyncGenerator
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from services.backtest_service import run_momentum_backtest, build_backtest_results_html
from utils.config import load_config

logger = logging.getLogger(__name__)

_agent_llm = None


def _get_agent_llm():
    global _agent_llm
    if _agent_llm is None:
        config = load_config()
        _agent_llm = ChatOpenAI(
            api_key=os.environ["XAI_API_KEY"],
            base_url="https://api.x.ai/v1",
            model=config["llm"]["model"],
            temperature=0.2,
            max_tokens=1500,
        )
    return _agent_llm


SUPPORTED_PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"]
SUPPORTED_PERIODS = ["3mo", "6mo", "1y", "2y"]


@tool
def design_momentum_strategy(
    pair: str,
    direction: str = "auto",
    period: str = "1y",
    lookback: int = 20,
    momentum_threshold: float = 0.5,
    take_profit: float = 1.0,
    stop_loss: float = 0.5,
    position_size_pct: float = 10,
) -> str:
    """Design and immediately backtest a momentum FX strategy.

    Args:
        pair: Currency pair (EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD)
        direction: Trade direction bias — 'long', 'short', or 'auto' (follow momentum)
        period: Historical period to test (3mo, 6mo, 1y, 2y)
        lookback: Number of days for momentum calculation (5-60)
        momentum_threshold: Minimum momentum % to trigger entry (0.1-2.0)
        take_profit: Take profit % from entry (0.3-3.0)
        stop_loss: Stop loss % from entry (0.2-2.0)
        position_size_pct: Position size as % of capital (5-25)
    """
    pair = pair.upper().replace("/", "")
    if pair not in SUPPORTED_PAIRS:
        return f"Unsupported pair {pair}. Supported: {', '.join(SUPPORTED_PAIRS)}"
    if period not in SUPPORTED_PERIODS:
        return f"Unsupported period {period}. Supported: {', '.join(SUPPORTED_PERIODS)}"

    lookback = max(5, min(60, lookback))
    momentum_threshold = max(0.1, min(2.0, momentum_threshold))
    take_profit = max(0.3, min(3.0, take_profit))
    stop_loss = max(0.2, min(2.0, stop_loss))
    position_size_pct = max(5, min(25, position_size_pct))

    try:
        result = run_momentum_backtest(
            pair=pair, period=period, lookback=lookback,
            momentum_threshold=momentum_threshold,
            take_profit=take_profit, stop_loss=stop_loss,
            position_size_pct=position_size_pct,
        )
        if "error" in result:
            return result["error"]
        return build_backtest_results_html(result)
    except Exception as e:
        return f"Backtest error: {e}"


@tool
def compare_strategies(pair: str, configs: str) -> str:
    """Run multiple backtest configurations on the same pair and return a comparison table.

    Args:
        pair: Currency pair (e.g., EURUSD)
        configs: JSON array of strategy configs, each with keys: label, lookback, take_profit, stop_loss, period.
                 Example: [{"label":"Conservative","lookback":30,"take_profit":0.5,"stop_loss":0.3,"period":"1y"},
                           {"label":"Aggressive","lookback":10,"take_profit":1.5,"stop_loss":0.8,"period":"1y"}]
    """
    pair = pair.upper().replace("/", "")
    if pair not in SUPPORTED_PAIRS:
        return f"Unsupported pair {pair}. Supported: {', '.join(SUPPORTED_PAIRS)}"

    try:
        strategy_configs = json.loads(configs)
    except json.JSONDecodeError:
        return "Invalid JSON in configs parameter."

    if not isinstance(strategy_configs, list) or len(strategy_configs) < 2:
        return "Provide at least 2 strategy configs to compare."
    if len(strategy_configs) > 5:
        strategy_configs = strategy_configs[:5]

    results = []
    for cfg in strategy_configs:
        label = cfg.get("label", "Strategy")
        try:
            r = run_momentum_backtest(
                pair=pair,
                period=cfg.get("period", "1y"),
                lookback=cfg.get("lookback", 20),
                take_profit=cfg.get("take_profit", 1.0),
                stop_loss=cfg.get("stop_loss", 0.5),
            )
            if "error" in r:
                results.append({"label": label, "error": r["error"]})
            else:
                results.append({"label": label, "metrics": r["metrics"]})
        except Exception as e:
            results.append({"label": label, "error": str(e)})

    rows = ""
    for r in results:
        if "error" in r:
            rows += f"| {r['label']} | Error: {r['error']} | - | - | - | - |\n"
        else:
            m = r["metrics"]
            ret_sign = "+" if m["total_return"] >= 0 else ""
            rows += (
                f"| {r['label']} | {ret_sign}{m['total_return']:.2f}% "
                f"| {m['sharpe_ratio']:.2f} | {m['max_drawdown']:.2f}% "
                f"| {m['win_rate']:.1f}% | {m['total_trades']} |\n"
            )

    header = f"## Strategy Comparison: {pair}\n\n"
    header += "| Strategy | Return | Sharpe | Max DD | Win Rate | Trades |\n"
    header += "|----------|--------|--------|--------|----------|--------|\n"
    return header + rows


@tool
def suggest_parameters(scenario: str, pair: str) -> str:
    """Given a macro scenario and currency pair, suggest optimal backtest parameters.

    Args:
        scenario: Description of the macro scenario (e.g., "Hormuz deal reduces oil prices")
        pair: Currency pair to optimize for
    """
    pair = pair.upper().replace("/", "")
    if pair not in SUPPORTED_PAIRS:
        return f"Unsupported pair {pair}. Supported: {', '.join(SUPPORTED_PAIRS)}"

    scenarios = {
        "high_volatility": {"lookback": 10, "take_profit": 1.5, "stop_loss": 0.8, "momentum_threshold": 0.3},
        "trending": {"lookback": 30, "take_profit": 2.0, "stop_loss": 0.5, "momentum_threshold": 0.5},
        "range_bound": {"lookback": 5, "take_profit": 0.5, "stop_loss": 0.3, "momentum_threshold": 0.8},
        "geopolitical_shock": {"lookback": 5, "take_profit": 2.0, "stop_loss": 1.0, "momentum_threshold": 0.3},
        "default": {"lookback": 20, "take_profit": 1.0, "stop_loss": 0.5, "momentum_threshold": 0.5},
    }

    scenario_lower = scenario.lower()
    if any(w in scenario_lower for w in ["war", "conflict", "shock", "crisis", "hormuz", "invasion", "sanctions"]):
        params = scenarios["geopolitical_shock"]
        regime = "Geopolitical Shock"
    elif any(w in scenario_lower for w in ["trend", "momentum", "rally", "bull", "bear"]):
        params = scenarios["trending"]
        regime = "Trending"
    elif any(w in scenario_lower for w in ["volatile", "uncertainty", "election", "vix"]):
        params = scenarios["high_volatility"]
        regime = "High Volatility"
    elif any(w in scenario_lower for w in ["range", "stable", "consolidat", "flat"]):
        params = scenarios["range_bound"]
        regime = "Range-Bound"
    else:
        params = scenarios["default"]
        regime = "Default"

    return json.dumps({
        "pair": pair,
        "regime": regime,
        "scenario": scenario,
        "recommended_parameters": params,
        "rationale": f"For a {regime.lower()} regime, using lookback={params['lookback']} days, "
                     f"TP={params['take_profit']}%, SL={params['stop_loss']}%, "
                     f"momentum threshold={params['momentum_threshold']}%.",
    }, indent=2)


AGENT_TOOLS = [design_momentum_strategy, compare_strategies, suggest_parameters]
AGENT_TOOL_MAP = {t.name: t for t in AGENT_TOOLS}

STRATEGY_SYSTEM_PROMPT = """You are the MacroHero Backtest Strategy Agent. Your job is to design FX trading strategy rules and execute backtests.

SKILLS:
1. **Design Strategy**: Given a macro scenario or trade idea, determine optimal backtest parameters (lookback, TP, SL, momentum threshold) and run the backtest.
2. **Compare Strategies**: Run multiple parameter sets on the same pair and produce a comparison table to find the best configuration.
3. **Suggest Parameters**: Map macro scenarios to appropriate strategy parameters based on market regime classification.

WORKFLOW:
1. When given a trade idea (e.g., "Long EUR/USD on Hormuz deal"):
   - Use suggest_parameters to classify the regime and get recommended params
   - Use design_momentum_strategy to run the backtest with those params
   - Also run a conservative and aggressive variant for comparison

2. When asked to optimize a strategy:
   - Use compare_strategies with 3-4 parameter sets varying lookback and TP/SL ratios
   - Recommend the best risk-adjusted configuration (highest Sharpe with acceptable drawdown)

3. When given multiple strategies from a macro framework:
   - Backtest each recommended trade separately
   - Rank by risk-adjusted return

RESPONSE FORMAT:
- Always include the backtest results (metrics table, equity curve, trade log) from the tools
- Add a brief interpretation: is this strategy viable? What's the risk?
- Suggest parameter adjustments if results are poor

CONSTRAINTS:
- Supported pairs: EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD
- Periods: 3mo, 6mo, 1y, 2y
- Only momentum strategy is available currently
- Do NOT suggest technical analysis indicators — focus on macro-driven momentum strategies"""


async def run_strategy_agent(
    user_request: str,
    context: str = "",
) -> AsyncGenerator[dict, None]:
    """Run the backtest strategy agent on a user request.

    Yields events: {"type": "status"|"result", "text": str}
    """
    llm = _get_agent_llm()
    llm_with_tools = llm.bind_tools(AGENT_TOOLS)

    messages = [
        SystemMessage(content=STRATEGY_SYSTEM_PROMPT),
    ]
    if context:
        messages.append(SystemMessage(content=f"CONTEXT FROM PREVIOUS ANALYSIS:\n{context}"))
    messages.append(HumanMessage(content=user_request))

    yield {"type": "status", "text": "Designing strategy..."}

    max_iterations = 5
    for iteration in range(max_iterations):
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
            logger.error(f"Strategy agent error: {e}")
            yield {"type": "result", "text": f"Strategy agent error: {e}"}
            return

        if not tool_calls:
            yield {"type": "result", "text": full_text}
            return

        seen = set()
        unique_calls = []
        for tc in tool_calls:
            name = tc.get("name", "")
            if name and name not in seen:
                seen.add(name)
                unique_calls.append(tc)

        from langchain_core.messages import AIMessage, ToolMessage
        assistant_msg = AIMessage(content=full_text, tool_calls=[
            {"id": tc.get("id", f"call_{i}"), "name": tc["name"],
             "args": json.loads(tc["args"]) if isinstance(tc.get("args"), str) else tc.get("args", {})}
            for i, tc in enumerate(unique_calls)
        ])
        messages.append(assistant_msg)

        for tc in unique_calls:
            name = tc.get("name", "")
            tool_labels = {
                "design_momentum_strategy": "Running backtest...",
                "compare_strategies": "Comparing strategies...",
                "suggest_parameters": "Analyzing scenario...",
            }
            yield {"type": "status", "text": tool_labels.get(name, f"Using {name}...")}

            tool_fn = AGENT_TOOL_MAP.get(name)
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

        yield {"type": "status", "text": "Composing results..."}

    yield {"type": "result", "text": full_text if full_text else "Strategy agent completed without final response."}
