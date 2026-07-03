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


@router.get("/analysis/{symbol}")
async def get_analysis(
    symbol: str,
    period: str = Query("3mo"),
    current_user: User = Depends(get_current_user),
):
    """Get comprehensive technical analysis for a symbol."""
    return await _compute_analysis(symbol, period)
