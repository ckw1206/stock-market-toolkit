"""Paper-trading portfolio routes — simulated buys/sells at real quotes."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.schemas import PaperTradeRequest
from app.services.paper_trading import (
    execute_trade,
    get_portfolio_view,
    get_trade_history,
    InvalidSideError,
    InvalidQuantityError,
    InsufficientCashError,
    InsufficientSharesError,
    QuoteUnavailableError,
)

router = APIRouter(prefix="/api/paper", tags=["paper-trading"])


@router.post("/trade")
async def post_trade(
    body: PaperTradeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute a simulated buy/sell at the latest close."""
    try:
        return await execute_trade(db, current_user.id, body.symbol, body.side, body.qty)
    except (InvalidSideError, InvalidQuantityError, InsufficientCashError, InsufficientSharesError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except QuoteUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/portfolio")
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Open positions, cash, and mark-to-market P&L."""
    return await get_portfolio_view(db, current_user.id)


@router.get("/history")
async def get_history(
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trade history, most recent first."""
    trades = await get_trade_history(db, current_user.id, limit=limit)
    return {"trades": trades}
