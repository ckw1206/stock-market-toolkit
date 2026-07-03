"""Signal backtest service — historical hit rate & average return."""

import pandas as pd

from app.providers import market_provider
from app.services.signals import (
    score_series,
    signal_from_score,
    ProviderUnavailableError,
    NoDataError,
    ThinHistoryError,
)

MIN_BACKTEST_BARS = 120


def _aggregate_side(
    signal_mask: pd.Series,
    forward_returns: dict[int, pd.Series],
    horizons: tuple[int, ...],
    hit_when_positive: bool = True,
) -> dict:
    side: dict = {"signal_days": int(signal_mask.sum()), "horizons": {}}
    for h in horizons:
        ret = forward_returns[h]
        valid = ret.notna() & signal_mask
        count = int(valid.sum())
        if count == 0:
            side["horizons"][str(h)] = {"count": 0, "hit_rate": 0.0, "avg_return_pct": 0.0}
        else:
            rets = ret[valid]
            hits = int((rets > 0).sum()) if hit_when_positive else int((rets < 0).sum())
            side["horizons"][str(h)] = {
                "count": count,
                "hit_rate": round(hits / count, 2),
                "avg_return_pct": round(float(rets.mean() * 100), 2),
            }
    return side


async def backtest_signal(
    symbol: str, period: str = "2y", horizons: tuple[int, ...] = (5, 20)
) -> dict:
    """Replay the composite signal over historical daily bars.

    For each trading day t with enough lookback:
      1. Compute composite score using ONLY data up to t (no lookahead).
      2. Map score → signal via ``signal_from_score``.
      3. For BUY/SELL days, measure forward return = (close[t+H] - close[t]) / close[t].

    BUY hit = forward return > 0; SELL hit = forward return < 0.

    Returns per-side aggregates (count, hit_rate 0-1, avg_return_pct) for each horizon.

    Raises:
        ProviderUnavailableError: data provider unavailable
        NoDataError: no data returned
        ThinHistoryError: fewer than ~120 bars
    """
    try:
        result = await market_provider.get_history(
            symbol.upper(), period=period, interval="1d"
        )
    except RuntimeError as exc:
        raise ProviderUnavailableError(f"Data provider unavailable for {symbol}") from exc

    df = result.value

    if df.empty:
        raise NoDataError(f"No data for {symbol}")

    if len(df) < MIN_BACKTEST_BARS:
        raise ThinHistoryError(symbol, len(df), MIN_BACKTEST_BARS)

    close = df["Close"]
    n = len(df)

    scores = score_series(df)
    signals = scores.map(signal_from_score)

    forward_returns: dict[int, pd.Series] = {}
    for h in horizons:
        forward_returns[h] = (close.shift(-h) - close) / close

    buy_mask = signals == "BUY"
    sell_mask = signals == "SELL"

    buy = _aggregate_side(buy_mask, forward_returns, horizons, hit_when_positive=True)
    sell = _aggregate_side(sell_mask, forward_returns, horizons, hit_when_positive=False)

    return {
        "symbol": symbol.upper(),
        "period": period,
        "bars": n,
        "buy": buy,
        "sell": sell,
    }


__all__ = ["backtest_signal", "ProviderUnavailableError", "NoDataError", "ThinHistoryError"]