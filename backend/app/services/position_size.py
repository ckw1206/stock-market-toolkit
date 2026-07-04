"""ATR-based position-size and stop-loss calculator.

Turns a signal into an actionable long-entry plan: given an account size and a
risk tolerance, how many shares to buy, where to place the stop, and where the
2R/3R take-profit levels sit. Uses Average True Range (ATR) for the stop
distance so it scales with the symbol's own volatility instead of a fixed %.
"""

import pandas_ta as ta

from app.providers import market_provider
from app.services.signals import (
    MIN_HISTORY_BARS,
    ProviderUnavailableError,
    NoDataError,
    ThinHistoryError,
)

ATR_LENGTH = 14


class InvalidPositionSizeInputError(Exception):
    """Raised when account/risk_pct/atr_mult are out of valid range."""


def compute_position_size(
    df,
    account: float,
    risk_pct: float,
    atr_mult: float = 2.0,
) -> dict:
    """Compute entry/stop/shares/take-profit from OHLC data and risk inputs.

    Assumes a long entry at the latest close, with the stop placed
    ``atr_mult`` ATRs below it. Returns zero shares (rather than raising) when
    the computed risk-per-share is non-positive, since that only happens for
    degenerate ATR values.
    """
    if account <= 0:
        raise InvalidPositionSizeInputError("account must be positive")
    if not (0 < risk_pct <= 100):
        raise InvalidPositionSizeInputError("risk_pct must be between 0 and 100")
    if atr_mult <= 0:
        raise InvalidPositionSizeInputError("atr_mult must be positive")

    atr_series = ta.atr(df["High"], df["Low"], df["Close"], length=ATR_LENGTH)
    atr = float(atr_series.iloc[-1]) if atr_series is not None and atr_series.notna().any() else None
    entry = float(df["Close"].iloc[-1])

    if atr is None or atr <= 0:
        return {
            "entry": round(entry, 2),
            "atr": None,
            "stop": None,
            "shares": 0,
            "risk_amount": 0.0,
            "take_profit_2r": None,
            "take_profit_3r": None,
        }

    stop = entry - atr_mult * atr
    risk_per_share = entry - stop

    if risk_per_share <= 0:
        shares = 0
    else:
        risk_budget = account * (risk_pct / 100.0)
        shares = int(risk_budget // risk_per_share)

    return {
        "entry": round(entry, 2),
        "atr": round(atr, 4),
        "stop": round(stop, 2),
        "shares": shares,
        "risk_amount": round(shares * risk_per_share, 2),
        "take_profit_2r": round(entry + 2 * risk_per_share, 2),
        "take_profit_3r": round(entry + 3 * risk_per_share, 2),
    }


async def get_position_size(
    symbol: str,
    account: float,
    risk_pct: float,
    atr_mult: float = 2.0,
    period: str = "6mo",
    provider=None,
) -> dict:
    """Fetch history for ``symbol`` and compute its position-size plan.

    Raises:
        ProviderUnavailableError: when the data provider is unavailable
        NoDataError: when no data is returned for the symbol
        ThinHistoryError: when there's not enough price history
        InvalidPositionSizeInputError: when account/risk_pct/atr_mult are invalid
    """
    if provider is None:
        provider = market_provider

    try:
        result = await provider.get_history(symbol.upper(), period=period, interval="1d")
    except RuntimeError as exc:
        raise ProviderUnavailableError(f"Data provider unavailable for {symbol}") from exc

    df = result.value

    if df.empty:
        raise NoDataError(f"No data for {symbol}")

    if len(df) < MIN_HISTORY_BARS:
        raise ThinHistoryError(symbol, len(df), MIN_HISTORY_BARS)

    plan = compute_position_size(df, account=account, risk_pct=risk_pct, atr_mult=atr_mult)
    return {"symbol": symbol.upper(), "account": account, "risk_pct": risk_pct, "atr_mult": atr_mult, **plan}
