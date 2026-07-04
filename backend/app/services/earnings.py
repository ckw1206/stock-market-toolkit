"""Earnings-date awareness — warn when a signal fires near an earnings report.

A technically perfect setup two days before earnings is a coin flip; this
surfaces the next upcoming earnings date so it can temper signal confidence
instead of silently being ignored.
"""

import asyncio
import logging
from datetime import date, datetime
from typing import Optional

import yfinance as yf

from app.services.cache import cached, cache_key

log = logging.getLogger(__name__)

EARNINGS_TTL = 86400  # 24h — earnings dates change rarely


def _fetch_next_earnings_date(symbol: str) -> Optional[str]:
    """Synchronous yfinance calendar lookup. Returns an ISO date string or None.

    yfinance's ``calendar`` shape has shifted across versions (dict of lists,
    dict of scalars, ``None``), so this is deliberately permissive about what
    it accepts and never raises past this point — the caller treats any
    failure the same as "no upcoming earnings date known".
    """
    ticker = yf.Ticker(symbol.upper())
    calendar = ticker.calendar or {}
    dates = calendar.get("Earnings Date") or []
    if not isinstance(dates, (list, tuple)):
        dates = [dates]

    today = date.today()
    future = []
    for d in dates:
        if isinstance(d, datetime):
            d = d.date()
        if not isinstance(d, date):
            continue
        if d >= today:
            future.append(d)

    return min(future).isoformat() if future else None


async def get_next_earnings_date(symbol: str) -> Optional[str]:
    """Cached (24h) lookup of the next upcoming earnings date, as an ISO date string.

    Returns None on any failure — earnings enrichment must never break the
    signal pipeline.
    """
    key = cache_key("earnings", symbol.upper())

    async def loader() -> Optional[str]:
        return await asyncio.to_thread(_fetch_next_earnings_date, symbol)

    try:
        return await cached(key, EARNINGS_TTL, loader)
    except Exception as exc:
        log.warning("Earnings lookup failed for %s: %s", symbol, exc)
        return None


def days_until(iso_date: Optional[str]) -> Optional[int]:
    """Calendar-day count from today to an ISO date string, or None."""
    if iso_date is None:
        return None
    try:
        target = date.fromisoformat(iso_date)
    except ValueError:
        return None
    return (target - date.today()).days
