"""Shared universe of tracked symbols."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Watchlist

TRACKED_SYMBOLS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "WMT"]


def get_tracked_universe() -> list[str]:
    return TRACKED_SYMBOLS


async def get_watchlist_symbols(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Watchlist.symbol).distinct())
    return [row[0] for row in result.fetchall()]


async def get_scan_universe(db: AsyncSession) -> list[str]:
    tracked = set(get_tracked_universe())
    watchlist_syms = await get_watchlist_symbols(db)
    tracked.update(watchlist_syms)
    return sorted(tracked)
