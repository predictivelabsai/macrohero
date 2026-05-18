"""Curated factor universe for FX scenario projections.

The LLM is constrained to this list when calling the projection tool. Each
entry pairs a canonical name (what the LLM sees) with a Massive ticker and
a transform that determines the unit of the shock the LLM must produce.
"""

from dataclasses import dataclass
from typing import Literal

AssetClass = Literal["commodity", "rates", "equity", "fx", "crypto"]
Transform = Literal["log_return", "abs_change_bp"]


@dataclass(frozen=True)
class FactorSpec:
    name: str
    massive_ticker: str
    asset_class: AssetClass
    description: str
    transform: Transform


FACTOR_UNIVERSE: tuple[FactorSpec, ...] = (
    # ----- Commodities (ETF proxies on Massive free Stocks tier) -----
    FactorSpec(
        "WTI crude", "USO", "equity",
        "US Oil Fund ETF — tracks WTI crude oil",
        "log_return",
    ),
    FactorSpec(
        "Brent crude", "BNO", "equity",
        "US Brent Oil Fund ETF — tracks Brent crude",
        "log_return",
    ),
    FactorSpec("Gold", "GLD", "equity", "SPDR Gold Shares ETF", "log_return"),
    FactorSpec("Silver", "SLV", "equity", "iShares Silver Trust ETF", "log_return"),
    FactorSpec("Copper", "CPER", "equity", "US Copper Index Fund ETF", "log_return"),
    FactorSpec(
        "Natural gas", "UNG", "equity",
        "US Natural Gas Fund ETF — tracks front-month natgas futures",
        "log_return",
    ),
    FactorSpec("Agriculture", "DBA", "equity", "Invesco Agriculture Fund ETF", "log_return"),
    FactorSpec(
        "Broad commodities", "DBC", "equity",
        "Invesco DB Commodity Index Tracking Fund — diversified basket",
        "log_return",
    ),
    # ----- US equities -----
    FactorSpec("S&P 500", "SPY", "equity", "SPDR S&P 500 ETF", "log_return"),
    FactorSpec("Nasdaq 100", "QQQ", "equity", "Invesco QQQ Nasdaq 100 ETF", "log_return"),
    FactorSpec(
        "Russell 2000", "IWM", "equity",
        "iShares Russell 2000 ETF — US small-caps",
        "log_return",
    ),
    # ----- Sector rotation (subset of S&P sectors most relevant to FX) -----
    FactorSpec(
        "Energy sector", "XLE", "equity",
        "Energy Select Sector SPDR — oil & gas equities; risk-on/oil signal",
        "log_return",
    ),
    FactorSpec(
        "Financials sector", "XLF", "equity",
        "Financial Select Sector SPDR — banks & financials; rates-sensitive",
        "log_return",
    ),
    FactorSpec(
        "Utilities sector", "XLU", "equity",
        "Utilities Select Sector SPDR — defensive, bond-like",
        "log_return",
    ),
    FactorSpec(
        "Healthcare sector", "XLV", "equity",
        "Health Care Select Sector SPDR — defensive sector",
        "log_return",
    ),
    # ----- International equities -----
    FactorSpec(
        "Europe equities", "FEZ", "equity", "SPDR Euro Stoxx 50 ETF", "log_return"
    ),
    FactorSpec(
        "Japan equities", "EWJ", "equity",
        "iShares MSCI Japan ETF",
        "log_return",
    ),
    FactorSpec(
        "Emerging markets equities", "EEM", "equity",
        "iShares MSCI Emerging Markets ETF — broad EM equity exposure",
        "log_return",
    ),
    FactorSpec(
        "China large-cap equities", "FXI", "equity",
        "iShares China Large-Cap ETF — Hong Kong-listed China big-caps",
        "log_return",
    ),
    FactorSpec(
        "China A-shares", "MCHI", "equity",
        "iShares MSCI China ETF — onshore + offshore China exposure",
        "log_return",
    ),
    FactorSpec(
        "Brazil equities", "EWZ", "equity",
        "iShares MSCI Brazil ETF — Brazil large-cap equity",
        "log_return",
    ),
    FactorSpec(
        "India equities", "INDA", "equity",
        "iShares MSCI India ETF",
        "log_return",
    ),
    # ----- US rates via Treasury bond ETFs (price inverse to yield) -----
    FactorSpec(
        "US 20+Y Treasury",
        "TLT",
        "equity",
        "iShares 20+ Year Treasury Bond ETF"
        " — price is inversely related to long yields (price up = yield down)",
        "log_return",
    ),
    FactorSpec(
        "US 7-10Y Treasury",
        "IEF",
        "equity",
        "iShares 7-10Y Treasury Bond ETF"
        " — price is inversely related to 10Y yield (price up = yield down)",
        "log_return",
    ),
    FactorSpec(
        "US 1-3Y Treasury",
        "SHY",
        "equity",
        "iShares 1-3 Year Treasury Bond ETF"
        " — price is inversely related to short yields (price up = yield down)",
        "log_return",
    ),
    FactorSpec(
        "US TIPS", "TIP", "equity",
        "iShares TIPS Bond ETF — inflation-protected Treasuries;"
        " rises with real-yield-down / breakeven-up",
        "log_return",
    ),
    FactorSpec(
        "Inflation expectations", "RINF", "equity",
        "ProShares Inflation Expectations ETF — long TIPS / short Treasuries;"
        " rises when breakeven inflation rises",
        "log_return",
    ),
    # ----- Credit -----
    FactorSpec(
        "High-yield credit", "HYG", "equity",
        "iShares iBoxx High Yield Corporate Bond ETF — risk-on / risk-off gauge",
        "log_return",
    ),
    FactorSpec(
        "Investment-grade credit", "LQD", "equity",
        "iShares iBoxx Investment Grade Corporate Bond ETF",
        "log_return",
    ),
    FactorSpec(
        "EM dollar bonds", "EMB", "equity",
        "iShares J.P. Morgan USD Emerging Markets Bond ETF — EM USD-debt risk",
        "log_return",
    ),
    # ----- Risk / volatility -----
    FactorSpec(
        "VIX (volatility)", "VXX", "equity",
        "iPath Series B S&P 500 VIX Short-Term Futures ETN — equity vol proxy",
        "log_return",
    ),
    # ----- FX ETFs -----
    FactorSpec(
        "Dollar Index", "UUP", "equity",
        "Invesco DB US Dollar Index Bullish Fund — broad USD strength",
        "log_return",
    ),
    FactorSpec(
        "Euro", "FXE", "equity", "Invesco CurrencyShares Euro Trust", "log_return"
    ),
    FactorSpec(
        "Japanese yen", "FXY", "equity",
        "Invesco CurrencyShares Japanese Yen Trust", "log_return",
    ),
    FactorSpec(
        "British pound", "FXB", "equity",
        "Invesco CurrencyShares British Pound Sterling Trust", "log_return",
    ),
    FactorSpec(
        "Australian dollar", "FXA", "equity",
        "Invesco CurrencyShares Australian Dollar Trust", "log_return",
    ),
    FactorSpec(
        "Canadian dollar", "FXC", "equity",
        "Invesco CurrencyShares Canadian Dollar Trust", "log_return",
    ),
    FactorSpec(
        "Swiss franc", "FXF", "equity",
        "Invesco CurrencyShares Swiss Franc Trust", "log_return",
    ),
    # ----- Crypto (native Massive symbols) -----
    FactorSpec(
        "Bitcoin", "X:BTCUSD", "crypto",
        "Bitcoin / USD spot (native Massive crypto)",
        "log_return",
    ),
    FactorSpec(
        "Ethereum", "X:ETHUSD", "crypto",
        "Ethereum / USD spot (native Massive crypto)",
        "log_return",
    ),
)

_BY_NAME: dict[str, FactorSpec] = {f.name: f for f in FACTOR_UNIVERSE}


def get_factor_by_name(name: str) -> FactorSpec:
    """Look up a factor spec by its canonical name. Raises KeyError if absent."""
    try:
        return _BY_NAME[name]
    except KeyError as exc:
        raise KeyError(f"Unknown factor: {name!r}") from exc
