from fastapi import APIRouter, Depends, HTTPException, Query
import logging

from app.models import User
from app.auth import get_current_user
from app.providers import market_provider

from app.services.signals import (
    compute_analysis_impl,
    ProviderUnavailableError,
    NoDataError,
    ThinHistoryError,
)
from app.services.backtest import (
    backtest_signal,
    ProviderUnavailableError as BacktestProviderUnavailableError,
    NoDataError as BacktestNoDataError,
    ThinHistoryError as BacktestThinHistoryError,
)
from app.services.position_size import get_position_size, InvalidPositionSizeInputError
from app.services.cache import cached

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analysis"])


async def _compute_analysis(symbol: str, period: str = "3mo") -> dict:
    """Get comprehensive technical analysis for a symbol (no auth dependency)."""
    try:
        return await compute_analysis_impl(symbol, period, provider=market_provider)
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=502, detail=str(exc)
        ) from exc
    except NoDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ThinHistoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


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


async def _backtest_signal(symbol: str, period: str = "2y") -> dict:
    """Backtest historical signal performance (no auth dependency)."""
    try:
        return await cached(
            key=f"backtest:{symbol.upper()}:{period}",
            ttl=3600,
            loader=lambda: backtest_signal(symbol, period=period),
        )
    except BacktestProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except BacktestNoDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except BacktestThinHistoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/analysis/{symbol}/backtest")
async def get_backtest(
    symbol: str,
    period: str = Query("2y"),
    current_user: User = Depends(get_current_user),
):
    """Backtest historical BUY/SELL signal hit rate and average return."""
    return await _backtest_signal(symbol, period)


@router.get("/analysis/{symbol}")
async def get_analysis(
    symbol: str,
    period: str = Query("3mo"),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive technical analysis for a symbol."""
    return await _compute_analysis(symbol, period)


@router.get("/analysis/{symbol}/position-size")
async def get_position_size_route(
    symbol: str,
    account: float = Query(..., gt=0, description="Account size in currency units"),
    risk_pct: float = Query(1.0, gt=0, le=100, description="Percent of account to risk on this trade"),
    atr_mult: float = Query(2.0, gt=0, description="Stop distance as a multiple of ATR(14)"),
    current_user: User = Depends(get_current_user),
):
    """ATR-based position size, stop-loss, and take-profit levels for a long entry."""
    try:
        return await get_position_size(
            symbol, account=account, risk_pct=risk_pct, atr_mult=atr_mult, provider=market_provider
        )
    except ProviderUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except NoDataError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except ThinHistoryError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except InvalidPositionSizeInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
