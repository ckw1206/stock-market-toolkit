from fastapi import APIRouter, Depends, Query
from app.models import User
from app.auth import get_current_user
from app.database import AsyncSessionLocal, get_db
from app.services.top_signals import get_top_signals

router = APIRouter(prefix="/api/signals", tags=["signals"])


@router.get("/top")
async def get_signals_top(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
):
    async with AsyncSessionLocal() as db:
        result = await get_top_signals(db, limit=limit)
    return result