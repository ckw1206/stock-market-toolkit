"""Market-wide stats (breadth) over the latest nightly signal scan."""

from fastapi import APIRouter, Depends

from app.auth import get_current_user
from app.database import AsyncSessionLocal
from app.models import User
from app.services.market_breadth import get_market_breadth

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/breadth")
async def get_breadth(current_user: User = Depends(get_current_user)):
    """Latest market-breadth snapshot plus trailing history for a sparkline."""
    async with AsyncSessionLocal() as db:
        return await get_market_breadth(db)
