import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from app.models import User
from app.schemas import StockDataResponse, IndicatorsResponse, CompareRequest, CompareResponse, CompareStockData
from app.auth import get_current_user
from app.providers import market_provider
from app.utils.numeric import _clean_list
import pandas_ta as ta
import math

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["stocks"])

# Approximate number of trading bars returned by yfinance for each period at
# the 1-day interval (used to estimate how many rows the display period spans).
# Intraday intervals (5m, 15m) return many more rows per calendar day, but the
# period → bar-count relationship is monotonic, so these estimates are
# conservative lower bounds that guarantee we never under-trim.
_APPROX_DISPLAY_BARS = {
    "1d": 1,
    "5d": 5,
    "1w": 5,
    "1mo": 21,
    "3mo": 63,
    "6mo": 126,
    "1y": 252,
    "2y": 504,
    "5y": 1260,
    "max": 2520,
}


def _estimate_display_rows(period: str, n_total: int) -> int:
    """Return the approximate number of display-period rows in *n_total*.

    When ``lookback_extra`` padding is applied, ``n_total`` (the padded
    DataFrame length) = display_rows + lookback_extra.  This function
    inverts that relationship to find display_rows, so the caller can
    compute ``trim = n_total - display_rows`` and strip the leading
    ``trim`` rows.

    Returns the lesser of ``n_total`` and the expected display-row count,
    so it is safe to call even when the actual data returned is shorter
    than the theoretical display period (e.g. thin trading history).
    """
    expected = _APPROX_DISPLAY_BARS.get(period, 21)
    return min(n_total, expected)


@router.get("/stock/{symbol}", response_model=StockDataResponse)
async def get_stock(
    symbol: str,
    period: str = Query("1mo"),
    current_user: User = Depends(get_current_user),
):
    if period not in ("1d", "5d", "1w", "1mo", "3mo", "6mo", "1y", "2y", "5y", "max"):
        raise HTTPException(status_code=400, detail="Invalid period")

    interval_map = {"1d": "5m", "5d": "15m"}
    interval = interval_map.get(period, "1d")

    try:
        result = await market_provider.get_history(
            symbol.upper(), period=period, interval=interval
        )
    except Exception as exc:
        log.error("Provider error for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Stock data service temporarily unavailable. Please try again later."
        )

    df = result.value

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data found for {symbol}")

    return StockDataResponse(
        symbol=symbol.upper(),
        period=period,
        cached_at=datetime.now(timezone.utc).isoformat(),
        source=result.source,
        as_of=result.as_of,
        timestamp=df.index.strftime("%Y-%m-%dT%H:%M:%S").tolist(),
        open=_clean_list(df["Open"].tolist()),
        high=_clean_list(df["High"].tolist()),
        low=_clean_list(df["Low"].tolist()),
        close=_clean_list(df["Close"].tolist()),
        volume=[int(v) if not math.isnan(v) else None for v in df["Volume"].tolist()],
    )


@router.get("/stock/{symbol}/indicators", response_model=IndicatorsResponse)
async def get_indicators(
    symbol: str,
    period: str = Query("3mo"),
    current_user: User = Depends(get_current_user),
):
    interval_map = {"1d": "5m", "5d": "15m"}
    interval = interval_map.get(period, "1d")

    # Maximum lookback needed by any indicator we compute.
    # SMA20=20, SMA50=50, SMA200=200, RSI=14, MACD uses its own internal windows
    # (12/26/9) which are fully contained within 35 extra bars; EMA uses the same
    # window as its corresponding SMA.  BBands and ATR also use length-20/14
    # windows.  The widest window among all computed indicators is SMA200=200.
    #
    # Only pad daily-interval requests: lookback_extra is expressed in calendar
    # days, and Yahoo caps intraday (5m/15m) data at ~60 days, so padding an
    # intraday period by 200 days returns an empty frame. Intraday periods
    # (1d/5d) already return enough bars for the short-window indicators.
    max_indicator_lookback = 200 if interval == "1d" else 0

    try:
        result = await market_provider.get_history(
            symbol.upper(), period=period, interval=interval,
            lookback_extra=max_indicator_lookback,
        )
    except Exception as exc:
        log.error("Provider error for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Stock data service temporarily unavailable. Please try again later."
        )

    df = result.value

    if len(df) < 2:
        raise HTTPException(status_code=404, detail=f"No data for {symbol} ({period})")

    close = df["Close"]
    n = len(close)

    def _safe_ta_series(fn, *args, **kwargs):
        """Call a ta function, return Series.tolist() or [None]*n on failure."""
        try:
            result = fn(*args, **kwargs)
            if result is None:
                return [None] * n
            if hasattr(result, "tolist"):
                return result.tolist()
            return list(result)
        except Exception:
            return [None] * n

    def _df_col(df, col):
        """Extract a column from DataFrame, or return [None]*n if unavailable."""
        if df is None or not hasattr(df, "columns") or col not in df.columns:
            return [None] * n
        return df[col].tolist()

    try:
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
        bbands_df = ta.bbands(close, length=20, std=2)
    except Exception:
        macd_df = None
        bbands_df = None

    rsi_vals = _safe_ta_series(ta.rsi, close, length=14)

    # Assemble full (padded) results
    raw = IndicatorsResponse(
        symbol=symbol.upper(),
        period=period,
        cached_at=datetime.now(timezone.utc).isoformat(),
        timestamp=df.index.strftime("%Y-%m-%dT%H:%M:%S").tolist(),
        sma20=_clean_list(_safe_ta_series(ta.sma, close, length=20)),
        sma50=_clean_list(
            _safe_ta_series(ta.sma, close, length=50)
            if n >= 50
            else [None] * n
        ),
        sma200=_clean_list(
            _safe_ta_series(ta.sma, close, length=200)
            if n >= 200
            else [None] * n
        ),
        ema12=_clean_list(_safe_ta_series(ta.ema, close, length=12)),
        ema26=_clean_list(_safe_ta_series(ta.ema, close, length=26)),
        rsi=_clean_list(
            rsi_vals.tolist() if hasattr(rsi_vals, "tolist") else list(rsi_vals)
        ),
        macd=_clean_list(_df_col(macd_df, "MACD_12_26_9")),
        macd_signal=_clean_list(_df_col(macd_df, "MACDs_12_26_9")),
        macd_hist=_clean_list(_df_col(macd_df, "MACDh_12_26_9")),
        bb_upper=_clean_list(_df_col(bbands_df, "BBU_20_2.0_2.0")),
        bb_middle=_clean_list(_df_col(bbands_df, "BBM_20_2.0_2.0")),
        bb_lower=_clean_list(_df_col(bbands_df, "BBL_20_2.0_2.0")),
        atr=_clean_list(
            _safe_ta_series(ta.atr, df["High"], df["Low"], df["Close"], length=14)
        ),
    )

    # Trim padded leading rows so the response covers exactly the display period.
    # Only applies when daily padding was requested; _APPROX_DISPLAY_BARS is a
    # daily bar-count table, so trimming an unpadded intraday frame (where
    # len(df) far exceeds those counts) would wrongly discard valid bars.
    if max_indicator_lookback > 0:
        # The display period starts at the end of the DataFrame; the first
        # (n - n_original) rows are lookback padding and must be removed.
        n_original = _estimate_display_rows(period, len(df))
        trim = n - n_original
        if trim > 0:
            raw.timestamp = raw.timestamp[trim:]
            raw.sma20 = raw.sma20[trim:]
            raw.sma50 = raw.sma50[trim:]
            raw.sma200 = raw.sma200[trim:]
            raw.ema12 = raw.ema12[trim:]
            raw.ema26 = raw.ema26[trim:]
            raw.rsi = raw.rsi[trim:]
            raw.macd = raw.macd[trim:]
            raw.macd_signal = raw.macd_signal[trim:]
            raw.macd_hist = raw.macd_hist[trim:]
            raw.bb_upper = raw.bb_upper[trim:]
            raw.bb_middle = raw.bb_middle[trim:]
            raw.bb_lower = raw.bb_lower[trim:]
            raw.atr = raw.atr[trim:]

        # Assert post-trim length matches expected display rows.
        # This guards against trim logic silently shrinking the response when
        # the padded DataFrame is shorter than expected (thin-history symbols).
        assert len(raw.timestamp) == n_original, (
            f"Post-trim timestamp count {len(raw.timestamp)} != expected {n_original}; "
            f"check _APPROX_DISPLAY_BARS for period={period}"
        )

    return raw


@router.post("/compare", response_model=CompareResponse)
async def compare_stocks(
    data: CompareRequest,
    current_user: User = Depends(get_current_user),
):
    stocks = []
    interval_map = {"1d": "5m", "5d": "15m"}
    int_interval = interval_map.get(data.period, "1d")
    for symbol in data.symbols:
        try:
            result = await market_provider.get_history(
                symbol.upper(), period=data.period, interval=int_interval
            )
        except Exception as exc:
            log.error("Failed to get stock history for %s: %s", symbol, exc, exc_info=True)
            raise HTTPException(
                status_code=503,
                detail="Stock data service temporarily unavailable. Please try again later."
            )
        df = result.value

        if df.empty:
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")

        stocks.append(
            CompareStockData(
                symbol=symbol.upper(),
                timestamp=df.index.strftime("%Y-%m-%dT%H:%M:%S").tolist(),
                close=_clean_list(df["Close"].tolist()),
                volume=[
                    int(v) if not (isinstance(v, float) and math.isnan(v)) else None
                    for v in df["Volume"].tolist()
                ],
            )
        )

    return CompareResponse(stocks=stocks)
