# macrohero numerics

Stateless FastAPI compute service for FX analytics. Live at `api.macrohero.chat`.

It **computes and returns** — it does not persist. Run history, trade storage, and
any stateful concerns belong to the consumer (e.g. AssetHero, the TS `apps/api`).
Market data comes from [Massive](https://massive.dev) daily bars.

## Running locally

```bash
cd apps/numerics
uv sync            # or: pip install -e . && pip install pytest pytest-asyncio pytest-httpx ruff
uvicorn numerics.main:app --port 4003 --reload
```

Interactive docs at <http://localhost:4003/docs>.

### Environment

| Variable | Required | Purpose |
|---|---|---|
| `MASSIVE_API_KEY` | for live data | Massive market-data key. If unset, data endpoints return the `massive_unconfigured` error envelope (still HTTP 200). |
| `MASSIVE_CACHE_DIR` | optional | On-disk parquet cache dir (default `.cache/massive`). |
| `NUMERICS_SERVICE_KEY` | optional | If set, gates `/v1/*` behind an `X-Service-Key` header (see [Auth](#auth)). If unset, all callers are allowed. |

Secrets are referenced by name only; never log or commit their values.

## Conventions

- All app endpoints are under the **`/v1`** prefix. `/healthz` is unversioned and always open.
- **Domain problems return HTTP 200** with an error envelope in the body:
  `diagnostics.error = {"code": "...", "message": "..."}` and `metrics: null`, `trades: []`.
  Codes: `massive_unconfigured`, `invalid_pair`, `insufficient_data`, `massive_auth`, `massive_api`.
- **HTTP 422** is reserved for pydantic request-validation failures.
- **HTTP 401** only for a bad/missing `X-Service-Key` when the gate is enabled.
- Handlers are `async`; Massive is the only data source.

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness check (open, ungated) |
| GET | `/v1/catalog` | Strategies, supported pairs, and param ranges for building a UI |
| GET | `/v1/factors` | Factor universe (used by TS `pnpm gen:factors`) |
| POST | `/v1/projection` | Deterministic FX factor-shock projection |
| POST | `/v1/backtest/momentum` | Momentum FX backtest |

### `GET /v1/catalog`

Discovery payload so consumers never hardcode valid values. Param ranges are derived
from the backtest request model's own `Field` constraints (single source of truth).

```json
{
  "strategies": ["momentum"],
  "pairs": ["EUR/USD","GBP/USD","USD/JPY","USD/CHF","AUD/USD","USD/CAD"],
  "params": {
    "history_days": {"min":30,"max":2000,"default":365},
    "lookback": {"min":5,"max":60,"default":20},
    "momentum_threshold": {"min":0,"max":10,"default":0.5},
    "take_profit": {"min":0,"max":10,"default":1.0},
    "stop_loss": {"min":0,"max":10,"default":0.5},
    "position_size_pct": {"min":0,"max":100,"default":10}
  }
}
```

### `POST /v1/backtest/momentum`

```bash
curl -X POST localhost:4003/v1/backtest/momentum \
  -H 'Content-Type: application/json' \
  -d '{"pair":"EUR/USD","period":"1y","lookback":20,"take_profit":1.0,"stop_loss":0.5}'
```

Request fields (all optional except `pair`):

| Field | Default | Notes |
|---|---|---|
| `pair` | — | `EUR/USD`, `USDJPY`, `C:EURUSD`, etc. |
| `history_days` | 365 | **Canonical** window length (30–2000). |
| `period` | none | **Sugar** for `history_days`: `3mo`=90, `6mo`=180, `1y`=365, `2y`=730. Applied only when `history_days` is not explicitly set; an explicit `history_days` always wins. |
| `lookback` | 20 | Momentum window in days (5–60). |
| `momentum_threshold` | 0.5 | Min \|momentum\| % to enter. |
| `take_profit` / `stop_loss` | 1.0 / 0.5 | Bracket %. |
| `position_size_pct` | 10 | % of capital per trade. |
| `initial_capital` | 100000 | |

**`history_days` vs `period`:** `history_days` is the real parameter; `period` is a
convenience alias only. Pass one or the other. If you pass both, `history_days` is used.

Response:

```json
{
  "pair": "C:EURUSD",
  "strategy": "momentum",
  "params": { "...": "echoed request, including resolved history_days" },
  "metrics": { "total_return": 0.0, "total_pnl": 0.0, "win_rate": 0.0,
               "sharpe_ratio": 0.0, "max_drawdown": 0.0, "total_trades": 0,
               "annualized_return": 0.0, "final_capital": 100000 },
  "trades": [
    { "entry_date": "...", "exit_date": "...", "direction": "long",
      "entry_price": 0, "exit_price": 0, "target_price": 0, "stop_price": 0,
      "hit_target": true, "hit_stop": false, "pnl": 0, "pnl_pct": 0,
      "capital_after": 0, "units": 0, "symbol": "C:EURUSD" }
  ],
  "diagnostics": { "n_bars": 0, "n_trades": 0, "warnings": [], "error": null }
}
```

Each trade includes `units` (position size in units of the pair) and `symbol` (the
resolved pair) alongside the pnl fields, so a consumer can persist a trade table directly.

## Auth

The service can sit on the public internet, so `/v1/*` can be gated by a shared secret:

- Set `NUMERICS_SERVICE_KEY` in the environment.
- Callers must then send header `X-Service-Key: <that value>` on every `/v1/*` request.
- Mismatch or missing header → **HTTP 401**.
- If `NUMERICS_SERVICE_KEY` is **unset**, all callers are allowed (local dev, existing
  internal callers). `/healthz` is never gated.

```bash
curl -H 'X-Service-Key: <key>' localhost:4003/v1/catalog
```

## Coverage gaps

AssetHero's FX **dashboard** also needs data this compute service intentionally does
**not** provide. These are **out of scope** here — a human should decide where they live
(in AssetHero locally, or in a separate market-data service):

- **Live FX quotes / spot rates** — real-time or near-real-time pricing.
- **Treasury yield curves** — e.g. US Treasury yields for macro context.
- **Macro-news movers** — headline/news feeds and their market impact.

This service is a **stateless quant/compute** layer (projection + backtest over Massive
daily bars). Streaming quotes, yield feeds, and news aggregation are a different concern
with different data sources, caching, and freshness requirements, and should not be bolted
onto it.

## Tests

```bash
cd apps/numerics
pytest -q
ruff check
```

Tests mock the Massive SDK, so they need no network and no live key.
