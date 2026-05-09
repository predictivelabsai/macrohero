import uuid
import logging
import json
import numpy as np
from datetime import datetime
import yfinance as yf
from db.pool import fetch_one, execute_sql

logger = logging.getLogger(__name__)


def _fetch_fx_data(pair: str, period: str = "1y", interval: str = "1d") -> dict:
    ticker = f"{pair.upper()}=X"
    data = yf.Ticker(ticker).history(period=period, interval=interval)
    if data.empty:
        return {"dates": [], "closes": [], "highs": [], "lows": []}
    return {
        "dates": [d.strftime("%Y-%m-%d") for d in data.index],
        "closes": [float(c) for c in data["Close"].values],
        "highs": [float(h) for h in data["High"].values],
        "lows": [float(l) for l in data["Low"].values],
    }


def _calculate_metrics(trades: list[dict], initial_capital: float) -> dict:
    if not trades:
        return {"total_return": 0, "total_pnl": 0, "win_rate": 0, "sharpe_ratio": 0,
                "max_drawdown": 0, "total_trades": 0, "annualized_return": 0, "final_capital": initial_capital}

    total_pnl = sum(t["pnl"] for t in trades)
    final_capital = initial_capital + total_pnl
    total_return = (total_pnl / initial_capital) * 100
    winners = [t for t in trades if t["pnl"] > 0]
    win_rate = (len(winners) / len(trades)) * 100 if trades else 0

    returns = [t["pnl_pct"] / 100 for t in trades]
    sharpe = (np.mean(returns) / np.std(returns) * np.sqrt(252)) if len(returns) > 1 and np.std(returns) > 0 else 0

    equity = [initial_capital]
    for t in trades:
        equity.append(equity[-1] + t["pnl"])
    peak = equity[0]
    max_dd = 0
    for val in equity:
        if val > peak:
            peak = val
        dd = (peak - val) / peak * 100
        if dd > max_dd:
            max_dd = dd

    days = len(set(t.get("entry_date", "") for t in trades))
    years = max(days / 252, 0.01)
    ann_return = ((final_capital / initial_capital) ** (1 / years) - 1) * 100

    return {
        "total_return": round(total_return, 2),
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 1),
        "sharpe_ratio": round(float(sharpe), 2),
        "max_drawdown": round(max_dd, 2),
        "total_trades": len(trades),
        "annualized_return": round(ann_return, 2),
        "final_capital": round(final_capital, 2),
    }


def run_momentum_backtest(
    pair: str = "EURUSD",
    period: str = "1y",
    initial_capital: float = 100000,
    lookback: int = 20,
    momentum_threshold: float = 0.5,
    take_profit: float = 1.0,
    stop_loss: float = 0.5,
    position_size_pct: float = 10,
) -> dict:
    data = _fetch_fx_data(pair, period)
    if len(data["closes"]) < lookback + 5:
        return {"error": f"Not enough data for {pair} with lookback {lookback}"}

    closes = data["closes"]
    dates = data["dates"]
    trades = []
    capital = initial_capital

    i = lookback
    while i < len(closes) - 1:
        momentum = ((closes[i] - closes[i - lookback]) / closes[i - lookback]) * 100
        if abs(momentum) >= momentum_threshold:
            direction = "long" if momentum > 0 else "short"
            entry_price = closes[i]
            pos_size = capital * (position_size_pct / 100)
            units = pos_size / entry_price

            tp_price = entry_price * (1 + take_profit / 100) if direction == "long" else entry_price * (1 - take_profit / 100)
            sl_price = entry_price * (1 - stop_loss / 100) if direction == "long" else entry_price * (1 + stop_loss / 100)

            hit_tp = False
            hit_sl = False
            exit_price = closes[-1]
            exit_idx = len(closes) - 1

            for j in range(i + 1, min(i + 10, len(closes))):
                if direction == "long":
                    if data["highs"][j] >= tp_price:
                        exit_price = tp_price
                        exit_idx = j
                        hit_tp = True
                        break
                    if data["lows"][j] <= sl_price:
                        exit_price = sl_price
                        exit_idx = j
                        hit_sl = True
                        break
                else:
                    if data["lows"][j] <= tp_price:
                        exit_price = tp_price
                        exit_idx = j
                        hit_tp = True
                        break
                    if data["highs"][j] >= sl_price:
                        exit_price = sl_price
                        exit_idx = j
                        hit_sl = True
                        break
            else:
                exit_price = closes[min(i + 10, len(closes) - 1)]
                exit_idx = min(i + 10, len(closes) - 1)

            if direction == "long":
                pnl = (exit_price - entry_price) * units
            else:
                pnl = (entry_price - exit_price) * units
            pnl_pct = (pnl / pos_size) * 100
            capital += pnl

            trades.append({
                "entry_date": dates[i],
                "exit_date": dates[exit_idx],
                "direction": direction,
                "entry_price": round(entry_price, 5),
                "exit_price": round(exit_price, 5),
                "target_price": round(tp_price, 5),
                "stop_price": round(sl_price, 5),
                "hit_target": hit_tp,
                "hit_stop": hit_sl,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "capital_after": round(capital, 2),
                "symbol": pair.upper(),
            })
            i = exit_idx + 1
        else:
            i += 1

    metrics = _calculate_metrics(trades, initial_capital)
    run_id = str(uuid.uuid4())[:8]

    try:
        execute_sql("""
            INSERT INTO backtest_runs (run_id, strategy_id, status, config, results, started_at, completed_at)
            VALUES (:rid, 'momentum', 'completed', :config, :results, NOW(), NOW())
        """, {
            "rid": run_id,
            "config": json.dumps({"pair": pair, "period": period, "lookback": lookback,
                                   "momentum_threshold": momentum_threshold, "take_profit": take_profit,
                                   "stop_loss": stop_loss, "position_size_pct": position_size_pct,
                                   "initial_capital": initial_capital}),
            "results": json.dumps(metrics),
        })
        for idx, t in enumerate(trades):
            execute_sql("""
                INSERT INTO backtest_trades (run_id, trade_type, symbol, direction, entry_time, exit_time,
                    entry_price, exit_price, target_price, stop_price, hit_target, hit_stop,
                    pnl, pnl_pct, capital_after, reason)
                VALUES (:rid, 'backtest', :sym, :dir, :et, :xt, :ep, :xp, :tp, :sp, :ht, :hs, :pnl, :pp, :ca, :reason)
            """, {
                "rid": run_id, "sym": t["symbol"], "dir": t["direction"],
                "et": t["entry_date"], "xt": t["exit_date"],
                "ep": t["entry_price"], "xp": t["exit_price"],
                "tp": t["target_price"], "sp": t["stop_price"],
                "ht": t["hit_target"], "hs": t["hit_stop"],
                "pnl": t["pnl"], "pp": t["pnl_pct"], "ca": t["capital_after"],
                "reason": f"momentum {'>' if t['direction']=='long' else '<'} {momentum_threshold}%",
            })
    except Exception as e:
        logger.error(f"Failed to store backtest results: {e}")

    return {"run_id": run_id, "pair": pair, "strategy": "momentum", "metrics": metrics, "trades": trades}


def build_trade_row_html(t: dict, idx: int) -> str:
    dir_color = "#10b981" if t["direction"] == "long" else "#ef4444"
    pnl_color = "#10b981" if t["pnl"] >= 0 else "#ef4444"
    result_icon = "&#10003;" if t["hit_target"] else ("&#10007;" if t["hit_stop"] else "&#8212;")
    return (
        f'<tr id="trade-row-{idx}">'
        f'<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;">{t["entry_date"]}</td>'
        f'<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;color:{dir_color};font-weight:600;">{t["direction"].upper()}</td>'
        f'<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;">{t["entry_price"]:.5f}</td>'
        f'<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;">{t["exit_price"]:.5f}</td>'
        f'<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;color:{pnl_color};">${t["pnl"]:+,.2f}</td>'
        f'<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;color:{pnl_color};">{t["pnl_pct"]:+.2f}%</td>'
        f'<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;">{result_icon}</td>'
        f'</tr>'
    )


def build_streaming_header_html(pair: str, strategy: str) -> str:
    return (
        f'<div id="bt-streaming">'
        f'<p style="font-weight:700;font-size:1rem;margin-bottom:8px;">Backtesting: {strategy.title()} on {pair.upper()}</p>'
        f'<div style="overflow-x:auto;">'
        f'<table id="bt-live-table" style="width:100%;border-collapse:collapse;">'
        f'<thead><tr>'
        f'<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Date</th>'
        f'<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Dir</th>'
        f'<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Entry</th>'
        f'<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Exit</th>'
        f'<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">P&L</th>'
        f'<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">P&L%</th>'
        f'<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Hit</th>'
        f'</tr></thead>'
        f'<tbody id="bt-live-body"></tbody>'
        f'</table></div></div>'
    )


def run_momentum_backtest_streaming(
    pair: str = "EURUSD",
    period: str = "1y",
    initial_capital: float = 100000,
    lookback: int = 20,
    momentum_threshold: float = 0.5,
    take_profit: float = 1.0,
    stop_loss: float = 0.5,
    position_size_pct: float = 10,
):
    """Generator that yields each trade as it's computed, then final metrics."""
    data = _fetch_fx_data(pair, period)
    if len(data["closes"]) < lookback + 5:
        yield {"type": "error", "error": f"Not enough data for {pair} with lookback {lookback}"}
        return

    closes = data["closes"]
    dates = data["dates"]
    trades = []
    capital = initial_capital

    i = lookback
    trade_idx = 0
    while i < len(closes) - 1:
        momentum = ((closes[i] - closes[i - lookback]) / closes[i - lookback]) * 100
        if abs(momentum) >= momentum_threshold:
            direction = "long" if momentum > 0 else "short"
            entry_price = closes[i]
            pos_size = capital * (position_size_pct / 100)
            units = pos_size / entry_price

            tp_price = entry_price * (1 + take_profit / 100) if direction == "long" else entry_price * (1 - take_profit / 100)
            sl_price = entry_price * (1 - stop_loss / 100) if direction == "long" else entry_price * (1 + stop_loss / 100)

            hit_tp = False
            hit_sl = False
            exit_price = closes[-1]
            exit_idx = len(closes) - 1

            for j in range(i + 1, min(i + 10, len(closes))):
                if direction == "long":
                    if data["highs"][j] >= tp_price:
                        exit_price = tp_price
                        exit_idx = j
                        hit_tp = True
                        break
                    if data["lows"][j] <= sl_price:
                        exit_price = sl_price
                        exit_idx = j
                        hit_sl = True
                        break
                else:
                    if data["lows"][j] <= tp_price:
                        exit_price = tp_price
                        exit_idx = j
                        hit_tp = True
                        break
                    if data["highs"][j] >= sl_price:
                        exit_price = sl_price
                        exit_idx = j
                        hit_sl = True
                        break
            else:
                exit_price = closes[min(i + 10, len(closes) - 1)]
                exit_idx = min(i + 10, len(closes) - 1)

            if direction == "long":
                pnl = (exit_price - entry_price) * units
            else:
                pnl = (entry_price - exit_price) * units
            pnl_pct = (pnl / pos_size) * 100
            capital += pnl

            trade = {
                "entry_date": dates[i],
                "exit_date": dates[exit_idx],
                "direction": direction,
                "entry_price": round(entry_price, 5),
                "exit_price": round(exit_price, 5),
                "target_price": round(tp_price, 5),
                "stop_price": round(sl_price, 5),
                "hit_target": hit_tp,
                "hit_stop": hit_sl,
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "capital_after": round(capital, 2),
                "symbol": pair.upper(),
            }
            trades.append(trade)
            yield {"type": "trade", "trade": trade, "index": trade_idx}
            trade_idx += 1
            i = exit_idx + 1
        else:
            i += 1

    metrics = _calculate_metrics(trades, initial_capital)
    run_id = str(uuid.uuid4())[:8]

    try:
        execute_sql("""
            INSERT INTO backtest_runs (run_id, strategy_id, status, config, results, started_at, completed_at)
            VALUES (:rid, 'momentum', 'completed', :config, :results, NOW(), NOW())
        """, {
            "rid": run_id,
            "config": json.dumps({"pair": pair, "period": period, "lookback": lookback,
                                   "momentum_threshold": momentum_threshold, "take_profit": take_profit,
                                   "stop_loss": stop_loss, "position_size_pct": position_size_pct,
                                   "initial_capital": initial_capital}),
            "results": json.dumps(metrics),
        })
        for idx, t in enumerate(trades):
            execute_sql("""
                INSERT INTO backtest_trades (run_id, trade_type, symbol, direction, entry_time, exit_time,
                    entry_price, exit_price, target_price, stop_price, hit_target, hit_stop,
                    pnl, pnl_pct, capital_after, reason)
                VALUES (:rid, 'backtest', :sym, :dir, :et, :xt, :ep, :xp, :tp, :sp, :ht, :hs, :pnl, :pp, :ca, :reason)
            """, {
                "rid": run_id, "sym": t["symbol"], "dir": t["direction"],
                "et": t["entry_date"], "xt": t["exit_date"],
                "ep": t["entry_price"], "xp": t["exit_price"],
                "tp": t["target_price"], "sp": t["stop_price"],
                "ht": t["hit_target"], "hs": t["hit_stop"],
                "pnl": t["pnl"], "pp": t["pnl_pct"], "ca": t["capital_after"],
                "reason": f"momentum {'>' if t['direction']=='long' else '<'} {momentum_threshold}%",
            })
    except Exception as e:
        logger.error(f"Failed to store backtest results: {e}")

    yield {"type": "complete", "result": {"run_id": run_id, "pair": pair, "strategy": "momentum", "metrics": metrics, "trades": trades}}


def build_backtest_results_html(result: dict) -> str:
    metrics = result["metrics"]
    trades = result["trades"]
    pair = result["pair"]
    strategy = result.get("strategy", "momentum")
    run_id = result.get("run_id", "")

    ret_color = "#10b981" if metrics["total_return"] >= 0 else "#ef4444"

    metrics_html = f"""
<div style="margin-bottom:16px;">
<p style="font-weight:700;font-size:1rem;margin-bottom:8px;">Backtest Results: {strategy.title()} on {pair.upper()}</p>
<p style="font-size:0.75rem;color:#6b7280;">Run ID: {run_id}</p>
<table style="width:100%;border-collapse:collapse;margin-top:8px;">
<tr><td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;font-weight:600;">Total Return</td>
    <td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;color:{ret_color};font-weight:700;">{metrics['total_return']:+.2f}%</td></tr>
<tr><td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">Total P&L</td>
    <td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;color:{ret_color};">${metrics['total_pnl']:+,.2f}</td></tr>
<tr><td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">Win Rate</td>
    <td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">{metrics['win_rate']:.1f}%</td></tr>
<tr><td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">Sharpe Ratio</td>
    <td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">{metrics['sharpe_ratio']:.2f}</td></tr>
<tr><td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">Max Drawdown</td>
    <td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">{metrics['max_drawdown']:.2f}%</td></tr>
<tr><td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">Total Trades</td>
    <td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">{metrics['total_trades']}</td></tr>
<tr><td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">Annualized Return</td>
    <td style="padding:6px;font-size:0.85rem;border-bottom:1px solid #e5e7eb;">{metrics['annualized_return']:+.2f}%</td></tr>
<tr><td style="padding:6px;font-size:0.85rem;">Final Capital</td>
    <td style="padding:6px;font-size:0.85rem;">${metrics['final_capital']:,.2f}</td></tr>
</table></div>"""

    # Equity curve chart
    capitals = [100000] + [t["capital_after"] for t in trades]
    dates = ["Start"] + [t["exit_date"] for t in trades]
    chart_html = ""
    if len(trades) > 1:
        import json as _json
        chart_html = f"""
<div id="bt-chart" style="width:100%;height:280px;margin:12px 0;"></div>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
Plotly.newPlot('bt-chart', [{{
    x: {_json.dumps(dates)},
    y: {_json.dumps(capitals)},
    type: 'scatter', mode: 'lines+markers',
    line: {{color: '{ret_color}', width: 2}},
    fill: 'tozeroy', fillcolor: '{ret_color}22',
    name: 'Equity'
}}], {{
    title: 'Equity Curve', font: {{size: 11}},
    margin: {{l:60,r:20,t:35,b:40}},
    xaxis: {{showgrid:true, gridcolor:'#f3f4f6'}},
    yaxis: {{title:'Capital ($)', showgrid:true, gridcolor:'#f3f4f6'}},
    plot_bgcolor: 'white', paper_bgcolor: 'white'
}}, {{responsive: true}});
</script>"""

    # Trades table (show last 20)
    display_trades = trades[-20:] if len(trades) > 20 else trades
    trades_rows = ""
    for t in display_trades:
        dir_color = "#10b981" if t["direction"] == "long" else "#ef4444"
        pnl_color = "#10b981" if t["pnl"] >= 0 else "#ef4444"
        result_icon = "&#10003;" if t["hit_target"] else ("&#10007;" if t["hit_stop"] else "&#8212;")
        trades_rows += f"""<tr>
<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;">{t['entry_date']}</td>
<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;color:{dir_color};font-weight:600;">{t['direction'].upper()}</td>
<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;">{t['entry_price']:.5f}</td>
<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;">{t['exit_price']:.5f}</td>
<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;color:{pnl_color};">${t['pnl']:+,.2f}</td>
<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;color:{pnl_color};">{t['pnl_pct']:+.2f}%</td>
<td style="padding:4px 6px;font-size:0.75rem;border-bottom:1px solid #f3f4f6;">{result_icon}</td>
</tr>"""

    trades_html = f"""
<p style="font-weight:600;font-size:0.9rem;margin:12px 0 6px;">Trade Log ({len(trades)} trades{', showing last 20' if len(trades) > 20 else ''})</p>
<div style="overflow-x:auto;">
<table style="width:100%;border-collapse:collapse;">
<thead><tr>
<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Date</th>
<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Dir</th>
<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Entry</th>
<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Exit</th>
<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">P&L</th>
<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">P&L%</th>
<th style="text-align:left;padding:4px 6px;font-size:0.7rem;border-bottom:2px solid #e5e7eb;">Hit</th>
</tr></thead>
<tbody>{trades_rows}</tbody>
</table></div>"""

    return f"CHART_HTML:{metrics_html}{chart_html}{trades_html}"
