from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import User, Watchlist
from app.schemas import WatchlistCreate, WatchlistUpdate, WatchlistResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])

MAX_WATCHLIST_PER_USER = 100


@router.get("", response_model=list[WatchlistResponse])
async def list_watchlist(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist)
        .where(Watchlist.user_id == current_user.id)
        .order_by(Watchlist.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=WatchlistResponse, status_code=201)
async def add_to_watchlist(
    data: WatchlistCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    symbol = data.symbol.upper()

    # Check if already in watchlist
    existing = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user.id,
            Watchlist.symbol == symbol,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409, detail=f"{symbol} is already in your watchlist"
        )

    # Check max limit
    result = await db.execute(
        select(Watchlist).where(Watchlist.user_id == current_user.id)
    )
    count = len(result.scalars().all())
    if count >= MAX_WATCHLIST_PER_USER:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum of {MAX_WATCHLIST_PER_USER} watchlist items reached",
        )

    entry = Watchlist(user_id=current_user.id, symbol=symbol)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.patch("/{symbol}", response_model=WatchlistResponse)
async def update_watchlist_item(
    symbol: str,
    data: WatchlistUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user.id,
            Watchlist.symbol == symbol.upper(),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in watchlist")

    if data.note is not None:
        entry.note = data.note or None
    if data.tags is not None:
        entry.tags = sorted({t.strip().lower() for t in data.tags if t.strip()})

    await db.commit()
    await db.refresh(entry)
    return entry


@router.delete("/{symbol}", status_code=204)
async def remove_from_watchlist(
    symbol: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Watchlist).where(
            Watchlist.user_id == current_user.id,
            Watchlist.symbol == symbol.upper(),
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail=f"{symbol} not found in watchlist")

    await db.delete(entry)
    await db.commit()
