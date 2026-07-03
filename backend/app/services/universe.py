"""Shared universe of tracked symbols."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Watchlist

DEFAULT_TRACKED_SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "WMT",
]

# Backwards-compatible alias
TRACKED_SYMBOLS = DEFAULT_TRACKED_SYMBOLS


def get_tracked_universe() -> list[str]:
    """Base scan universe: SCAN_UNIVERSE env override, else the default US list.

    SCAN_UNIVERSE is a comma-separated symbol list and may mix markets,
    e.g. "AAPL,NVDA,2330.TW,2317.TW" (.TW/.TWO symbols are served by FinMind).
    """
    configured = get_settings().SCAN_UNIVERSE
    symbols = [s.strip().upper() for s in configured.split(",") if s.strip()]
    return symbols or DEFAULT_TRACKED_SYMBOLS


async def get_watchlist_symbols(db: AsyncSession) -> list[str]:
    result = await db.execute(select(Watchlist.symbol).distinct())
    return [row[0] for row in result.fetchall()]


async def get_scan_universe(db: AsyncSession) -> list[str]:
    tracked = set(get_tracked_universe())
    watchlist_syms = await get_watchlist_symbols(db)
    tracked.update(watchlist_syms)
    return sorted(tracked)
