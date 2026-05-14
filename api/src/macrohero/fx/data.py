"""Massive data client with on-disk parquet caching."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
from massive import RESTClient
from massive.exceptions import AuthError, BadResponse


class MassiveError(Exception):
    """Base for Massive data layer errors."""


class InvalidPairError(MassiveError):
    """Massive does not recognize the symbol (404)."""


class InsufficientDataError(MassiveError):
    """The response has no usable bars in the requested window."""


class MassiveAPIError(MassiveError):
    """5xx or other retryable failure that didn't recover."""


class MassiveAuthError(MassiveError):
    """401/403 from Massive -- auth misconfigured."""


def _symbol_safe(symbol: str) -> str:
    # Assumes valid Massive tickers don't differ only by `:` vs `_` vs `/`.
    # Today this holds (FX tickers all start with `C:`; equities have no separators).
    return symbol.replace(":", "_").replace("/", "_")


def _cache_path_for(cache_dir: Path, symbol: str, start: date, end: date) -> Path:
    safe = _symbol_safe(symbol)
    return cache_dir / safe / f"{start.isoformat()}_{end.isoformat()}.parquet"


def _yesterday_utc() -> date:
    # Massive publishes EOD bars after the session close. Bucket to "yesterday"
    # so we never cache an in-progress bar.
    return date.today() - timedelta(days=1)


class _StatusAwareRESTClient(RESTClient):
    """RESTClient that attaches the HTTP status code to BadResponse."""

    def _get(self, path, params=None, result_key=None, deserializer=None, raw=False, options=None):  # type: ignore[override]
        from massive.rest.models.request import RequestOptionBuilder

        option = options if options is not None else RequestOptionBuilder()
        headers = self._concat_headers(option.headers)

        resp = self.client.request(
            "GET",
            self.BASE + path,
            fields=params,
            headers=headers,
        )

        if resp.status != 200:
            exc = BadResponse(resp.data.decode("utf-8"))
            exc.http_status = resp.status  # type: ignore[attr-defined]
            raise exc

        if raw:
            return resp

        try:
            obj = self.json.loads(resp.data.decode("utf-8"))
        except ValueError:
            return []

        if result_key:
            if result_key not in obj:
                return []
            obj = obj[result_key]

        if deserializer:
            if isinstance(obj, list):
                obj = [deserializer(o) for o in obj]
            else:
                obj = deserializer(obj)

        return obj


def _map_exc(exc: BadResponse, context: str) -> MassiveError:
    """Translate a BadResponse (with attached http_status) to a typed Massive error."""
    status = getattr(exc, "http_status", None)
    if status in (401, 403):
        return MassiveAuthError(f"Massive auth failed ({status}): {context}")
    if status == 404:
        return InvalidPairError(f"Massive does not recognize {context}")
    if status is not None and status >= 500:
        return MassiveAPIError(f"Massive {status}: {context}")
    return MassiveAPIError(f"Massive error: {context} ({exc.args[0][:200] if exc.args else ''})")


class MassiveDataClient:
    """Async Massive client with read-through parquet cache."""

    def __init__(
        self,
        *,
        api_key: str,
        cache_dir: Path,
    ) -> None:
        self._api_key = api_key
        self._cache_dir = Path(cache_dir)
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._pair_cache: dict[str, str] = {}
        self._sdk = _StatusAwareRESTClient(api_key=api_key)

    async def fetch_bars(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Return a DataFrame with a single `close` column indexed by date."""
        # Clamp end to yesterday to keep the cache stable.
        effective_end = min(end, _yesterday_utc())
        if effective_end < start:
            raise InsufficientDataError(
                f"requested window [{start}, {end}] is before usable data"
            )

        cache_path = _cache_path_for(self._cache_dir, symbol, start, effective_end)
        if cache_path.exists():
            try:
                cached = pd.read_parquet(cache_path)
                cached.index = cached.index.astype("datetime64[s]")
                return cached
            except Exception:
                # Corrupt parquet (truncated write, disk full mid-write, etc.).
                # Delete and fall through to refetch — keep the failure transparent.
                cache_path.unlink(missing_ok=True)

        df = await self._fetch_bars_remote(symbol, start, effective_end)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_suffix(".parquet.tmp")
        df.to_parquet(tmp_path)
        tmp_path.replace(cache_path)
        return df

    async def _fetch_bars_remote(
        self, symbol: str, start: date, end: date
    ) -> pd.DataFrame:
        def _call() -> list:
            try:
                return list(
                    self._sdk.list_aggs(
                        symbol,
                        1,
                        "day",
                        start.isoformat(),
                        end.isoformat(),
                        limit=50000,
                    )
                )
            except BadResponse as exc:
                raise _map_exc(exc, symbol) from exc
            except AuthError as exc:
                raise MassiveAuthError(f"Massive auth failed: {exc}") from exc

        try:
            aggs = await asyncio.to_thread(_call)
        except MassiveError:
            raise

        if not aggs:
            raise InsufficientDataError(f"no bars returned for {symbol} [{start}, {end}]")

        rows = [
            {"date": pd.to_datetime(a.timestamp, unit="ms").date(), "close": a.close}
            for a in aggs
        ]
        df = pd.DataFrame(rows)
        df = df.set_index("date")
        df.index = pd.to_datetime(df.index)
        return df

    async def resolve_fx_pair(self, user_input: str) -> str:
        """Normalize user pair input (e.g. 'EUR/USD', 'eurusd') to 'C:EURUSD'."""
        cleaned = user_input.strip().upper().replace("/", "").replace(" ", "")
        if cleaned.startswith("C:"):
            cleaned = cleaned[2:]
        if len(cleaned) != 6:
            raise InvalidPairError(f"can't parse FX pair from {user_input!r}")
        candidate = f"C:{cleaned}"

        if candidate in self._pair_cache:
            return self._pair_cache[candidate]

        def _call() -> list:
            try:
                return list(
                    self._sdk.list_tickers(
                        ticker=candidate,
                        market="fx",
                        active=True,
                    )
                )
            except BadResponse as exc:
                raise _map_exc(exc, candidate) from exc
            except AuthError as exc:
                raise MassiveAuthError(f"Massive auth failed: {exc}") from exc

        try:
            results = await asyncio.to_thread(_call)
        except MassiveError:
            raise

        if not results:
            raise InvalidPairError(f"Massive does not list {candidate}")

        self._pair_cache[candidate] = candidate
        return candidate

    async def latest_close(self, symbol: str) -> tuple[float, date]:
        """Return the most recent end-of-day close + its date."""
        end = _yesterday_utc()
        start = end - timedelta(days=7)
        df = await self.fetch_bars(symbol, start, end)
        if df.empty:
            raise InsufficientDataError(f"no recent bars for {symbol}")
        last_idx = df.index.max()
        last_close = float(df.loc[last_idx, "close"])
        return last_close, pd.Timestamp(last_idx).date()
