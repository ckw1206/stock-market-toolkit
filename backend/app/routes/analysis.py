from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from app.models import User
from app.auth import get_current_user
from app.providers import market_provider
import pandas_ta as ta

from app.services.signals import (
    compute_indicators,
    is_breakout,
    score_signals,
    build_signal_result,
    MIN_HISTORY_BARS,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


async def _compute_analysis(symbol: str, period: str = "3mo") -> dict:
    """Get comprehensive technical analysis for a symbol (no auth dependency)."""
    interval_map = {"1d": "5m", "5d": "15m"}
    interval = interval_map.get(period, "1d")
    try:
        result = await market_provider.get_history(
            symbol.upper(), period=period, interval=interval
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=502, detail=f"Data provider unavailable for {symbol}"
        ) from exc
    df = result.value

    if df.empty:
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    if len(df) < MIN_HISTORY_BARS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Not enough price history for {symbol} to compute signals: "
                f"only {len(df)} trading day(s) available, need at least "
                f"{MIN_HISTORY_BARS}. The symbol may have been listed too "
                f"recently — check back once it has more trading history."
            ),
        )

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    n = len(close)
    latest_close = float(close.iloc[-1])

    try:
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    except Exception:
        macd_df = None

    indicators = compute_indicators(close, high, low, volume, n, macd_df)
    rvol = indicators.get("rvol")
    volume_spike = rvol is not None and rvol > 2.0

    high_52w = None
    low_52w = None
    breakout = False

    try:
        result_1y = await market_provider.get_history(
            symbol.upper(), period="1y", interval="1d"
        )
        df_1y = result_1y.value
        if not df_1y.empty:
            high_52w = float(df_1y["High"].max())
            low_52w = float(df_1y["Low"].min())
            breakout = is_breakout(latest_close, high_52w, rvol)
    except Exception:
        pass

    score, reasons = score_signals(
        bias=indicators.get("bias"),
        macd_hist=indicators.get("macd_histogram"),
        kdj_k=indicators.get("kdj_k"),
        kdj_d=indicators.get("kdj_d"),
        vol_ratio=indicators.get("volume_ratio"),
        rvol=rvol,
        breakout=breakout,
        high_52w=high_52w,
        close_price=latest_close,
    )

    return build_signal_result(
        symbol=symbol,
        period=period,
        latest_close=latest_close,
        timestamp=df.index[-1].isoformat() if len(df) > 0 else None,
        indicators=indicators,
        score=score,
        reasons=reasons,
        volume_spike=volume_spike,
        breakout=breakout,
        high_52w=high_52w,
        low_52w=low_52w,
    )


@router.get("/analysis/signals")
async def get_batch_signals(
    symbols: str = Query(..., description="Comma-separated list of symbols (max 25)"),
    period: str = Query("1mo"),
    current_user: User = Depends(get_current_user),
):
    """Get signals for multiple symbols.

    Returns ``{"signals": [...], "errors": [{"symbol", "error"}]}`` so the
    caller can surface a reason for symbols whose analysis failed instead of
    silently dropping them.
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if len(symbol_list) > 25:
        raise HTTPException(status_code=400, detail="Maximum 25 symbols allowed")
    results: list[dict] = []
    errors: list[dict] = []
    for sym in symbol_list:
        try:
            results.append(await _compute_analysis(sym, period))
        except HTTPException as exc:
            errors.append({"symbol": sym, "error": exc.detail})
        except Exception as exc:  # noqa: BLE001
            # Surface a concrete reason on the signal card instead of a generic
            # "analysis failed" — include the error type and message so the user
            # can tell an unexpected analysis bug apart from "no/thin data".
            log.warning("analysis failed for %s: %s", sym, exc, exc_info=True)
            reason = str(exc).strip() or exc.__class__.__name__
            errors.append(
                {"symbol": sym, "error": f"Could not analyze {sym}: {reason}"}
            )
    return {"signals": results, "errors": errors}


@router.get("/analysis/{symbol}")
async def get_analysis(
    symbol: str,
    period: str = Query("3mo"),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive technical analysis for a symbol."""
    return await _compute_analysis(symbol, period)
