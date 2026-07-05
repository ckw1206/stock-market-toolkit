"""Market-wide stats (breadth) over the latest nightly signal scan."""

from datetime import date

from fastapi import APIRouter, Depends, Query

from app.auth import get_current_user
from app.database import AsyncSessionLocal
from app.models import User
from app.services.market_breadth import get_market_breadth

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/breadth")
async def get_breadth(
    breadth_date: date | None = Query(
        None, description="Specific trading day (YYYY-MM-DD). Omit for latest + 29 prior days."
    ),
    current_user: User = Depends(get_current_user),
):
    """Latest market-breadth snapshot plus trailing history for a sparkline.

    When ?date=YYYY-MM-DD is provided, returns the single row for that trading
    day. Otherwise returns the latest row plus the prior 29 days (30 total).
    """
    async with AsyncSessionLocal() as db:
        return await get_market_breadth(db, breadth_date=breadth_date)
