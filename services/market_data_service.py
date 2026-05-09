import os
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


async def get_treasury_yields(year: int = None) -> list[dict]:
    """Fetch US Treasury yield rates from EODHD API."""
    api_key = os.environ.get("EODHD_API_KEY")
    if not api_key:
        return []
    if year is None:
        year = datetime.now().year

    import httpx
    url = f"https://eodhd.com/api/ust/yield-rates?api_token={api_key}&filter[year]={year}&fmt=json"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.error(f"EODHD yield rates error: {e}")
        return []


async def get_treasury_yields_multi_year(years: int = 1) -> list[dict]:
    """Fetch treasury yields for multiple years."""
    current_year = datetime.now().year
    all_data = []
    for y in range(current_year - years + 1, current_year + 1):
        data = await get_treasury_yields(y)
        all_data.extend(data)
    return all_data


async def get_fx_history(pair: str, period: str = "1y") -> dict:
    """Fetch FX rate history using yfinance."""
    import yfinance as yf
    ticker = f"{pair.upper()}=X"
    try:
        data = await asyncio.to_thread(lambda: yf.Ticker(ticker).history(period=period))
        if data.empty:
            return {"pair": pair, "dates": [], "rates": []}
        dates = [d.strftime("%Y-%m-%d") for d in data.index]
        rates = [round(float(r), 4) for r in data["Close"].values]
        return {"pair": pair, "dates": dates, "rates": rates}
    except Exception as e:
        logger.error(f"yfinance error for {pair}: {e}")
        return {"pair": pair, "dates": [], "rates": []}


def build_dual_axis_chart_html(
    title: str,
    dates: list[str],
    series1_values: list[float],
    series1_name: str,
    series2_values: list[float],
    series2_name: str,
    y1_label: str = "",
    y2_label: str = "",
) -> str:
    """Build a Plotly dual-axis line chart as a self-contained HTML string."""
    import json
    dates_json = json.dumps(dates)
    s1_json = json.dumps(series1_values)
    s2_json = json.dumps(series2_values)

    return f"""<div id="chart-container" style="width:100%;height:400px;"></div>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
var trace1 = {{
    x: {dates_json},
    y: {s1_json},
    name: '{series1_name}',
    type: 'scatter',
    mode: 'lines',
    line: {{color: '#3b82f6', width: 2}},
    yaxis: 'y'
}};
var trace2 = {{
    x: {dates_json},
    y: {s2_json},
    name: '{series2_name}',
    type: 'scatter',
    mode: 'lines',
    line: {{color: '#ef4444', width: 2}},
    yaxis: 'y2'
}};
var layout = {{
    title: '{title}',
    font: {{size: 11}},
    margin: {{l: 60, r: 60, t: 40, b: 40}},
    xaxis: {{title: '', showgrid: true, gridcolor: '#f3f4f6'}},
    yaxis: {{title: '{y1_label}', titlefont: {{color: '#3b82f6'}}, tickfont: {{color: '#3b82f6'}}, showgrid: true, gridcolor: '#f3f4f6'}},
    yaxis2: {{title: '{y2_label}', titlefont: {{color: '#ef4444'}}, tickfont: {{color: '#ef4444'}}, overlaying: 'y', side: 'right'}},
    legend: {{x: 0, y: 1.12, orientation: 'h'}},
    plot_bgcolor: 'white',
    paper_bgcolor: 'white'
}};
Plotly.newPlot('chart-container', [trace1, trace2], layout, {{responsive: true}});
</script>"""


def build_line_chart_html(
    title: str,
    dates: list[str],
    values: list[float],
    series_name: str,
    y_label: str = "",
    color: str = "#3b82f6",
) -> str:
    """Build a Plotly single-series line chart as a self-contained HTML string."""
    import json
    dates_json = json.dumps(dates)
    vals_json = json.dumps(values)

    return f"""<div id="chart-container" style="width:100%;height:350px;"></div>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<script>
var trace = {{
    x: {dates_json},
    y: {vals_json},
    name: '{series_name}',
    type: 'scatter',
    mode: 'lines',
    line: {{color: '{color}', width: 2}},
    fill: 'tozeroy',
    fillcolor: '{color}22'
}};
var layout = {{
    title: '{title}',
    font: {{size: 11}},
    margin: {{l: 50, r: 20, t: 40, b: 40}},
    xaxis: {{showgrid: true, gridcolor: '#f3f4f6'}},
    yaxis: {{title: '{y_label}', showgrid: true, gridcolor: '#f3f4f6'}},
    plot_bgcolor: 'white',
    paper_bgcolor: 'white'
}};
Plotly.newPlot('chart-container', [trace], layout, {{responsive: true}});
</script>"""


def build_table_html(title: str, headers: list[str], rows: list[list[str]]) -> str:
    """Build a styled HTML table."""
    header_cells = "".join(f'<th style="text-align:left;padding:6px;border-bottom:2px solid #e5e7eb;font-size:0.8rem;">{h}</th>' for h in headers)
    body_rows = ""
    for row in rows:
        cells = "".join(f'<td style="padding:6px;border-bottom:1px solid #f3f4f6;font-size:0.8rem;">{c}</td>' for c in row)
        body_rows += f"<tr>{cells}</tr>"
    return f"""<p style="font-weight:600;font-size:0.9rem;margin-bottom:8px;">{title}</p>
<table style="width:100%;border-collapse:collapse;"><thead><tr>{header_cells}</tr></thead><tbody>{body_rows}</tbody></table>"""
