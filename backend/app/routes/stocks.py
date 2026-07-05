import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from app.models import User
from app.schemas import StockDataResponse, IndicatorsResponse, CompareRequest, CompareResponse, CompareStockData
from app.auth import get_current_user
from app.providers import market_provider
from app.services.earnings import get_next_earnings_date, days_until
from app.utils.numeric import _clean_list
import pandas_ta as ta
import math

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["stocks"])


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
        cached_at=datetime.utcnow().isoformat(),
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

    if len(df) < 2:
        raise HTTPException(status_code=404, detail=f"No data for {symbol} ({period})")

    close = df["Close"]

    def _safe_ta_series(fn, *args, **kwargs):
        """Call a ta function, return Series.tolist() or [None]*n on failure."""
        n = len(close)
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
        n = len(close)
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

    return IndicatorsResponse(
        symbol=symbol.upper(),
        period=period,
        cached_at=datetime.utcnow().isoformat(),
        timestamp=df.index.strftime("%Y-%m-%dT%H:%M:%S").tolist(),
        sma20=_clean_list(_safe_ta_series(ta.sma, close, length=20)),
        sma50=_clean_list(
            _safe_ta_series(ta.sma, close, length=50)
            if len(close) >= 50
            else [None] * len(close)
        ),
        sma200=_clean_list(
            _safe_ta_series(ta.sma, close, length=200)
            if len(close) >= 200
            else [None] * len(close)
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


@router.get("/stock/{symbol}/earnings")
async def get_stock_earnings(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    """Return next earnings date and days-to-earnings for a symbol."""
    iso = await get_next_earnings_date(symbol.upper())
    return {
        "symbol": symbol.upper(),
        "next_earnings_date": iso,
        "days_to_earnings": days_until(iso),
    }
