"""Paper-trading portfolio routes — simulated buys/sells at real quotes."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.schemas import PaperTradeRequest, PaperPortfolioCreate
from app.services.paper_trading import (
    execute_trade,
    get_portfolio_view,
    get_trade_history,
    undo_trade,
    reset_portfolio,
    get_or_create_portfolio,
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
    if body.executed_at is not None:
        if body.executed_at.tzinfo is None:
            body.executed_at = body.executed_at.replace(tzinfo=timezone.utc)
        if body.executed_at > datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="executed_at cannot be in the future")
    try:
        return await execute_trade(
            db, current_user.id, body.symbol, body.side, body.qty, executed_at=body.executed_at
        )
    except (InvalidSideError, InvalidQuantityError, InsufficientCashError, InsufficientSharesError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except QuoteUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.delete("/trade/{trade_id}")
async def delete_trade(
    trade_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a trade and recompute portfolio cash and positions."""
    try:
        return await undo_trade(db, current_user.id, trade_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/reset")
async def post_reset(
    body: PaperPortfolioCreate | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete all trades and reset cash. Optionally set a new starting_cash."""
    starting_cash = body.starting_cash if body is not None else None
    return await reset_portfolio(db, current_user.id, starting_cash=starting_cash)


@router.post("/portfolio")
async def create_portfolio(
    body: PaperPortfolioCreate | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create (or return existing) portfolio with optional custom starting_cash."""
    starting_cash = body.starting_cash if body is not None else None
    await get_or_create_portfolio(db, current_user.id, starting_cash=starting_cash)
    return await get_portfolio_view(db, current_user.id)


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
