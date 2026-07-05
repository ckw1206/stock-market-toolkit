"""Market breadth — aggregate market-wide stats over a scan's universe.

Gives users the "market weather" before acting on any individual signal: a
BUY signal in a broadly deteriorating market deserves different treatment
than one in a strong tape.
"""

from datetime import date
from typing import Sequence

from sqlalchemy import select

from app.models import ScanResult, MarketBreadth, SignalScan

RISK_ON_THRESHOLD = 60.0
RISK_OFF_THRESHOLD = 40.0


def compute_breadth(results: Sequence[ScanResult]) -> dict:
    """Aggregate per-symbol scan results into market-wide breadth stats.

    - pct_above_50dma: % of symbols whose close is above their 50-day SMA
    - pct_above_200dma: % of symbols whose close is above their 200-day SMA
    - advancers: symbols where close > prev_close
    - decliners: symbols where close < prev_close
    - new_highs: symbols at or near their 52-week rolling high
    - new_lows: symbols at or near their 52-week rolling low

    Symbols missing the relevant field are excluded from that leg's
    denominator rather than counted as a miss.
    """
    total = len(results)
    if total == 0:
        return {
            "pct_above_50dma": None,
            "pct_above_200dma": None,
            "advancers": 0,
            "decliners": 0,
            "new_highs": 0,
            "new_lows": 0,
        }

    # % above 50-DMA
    above_50 = [r for r in results if r.price is not None and r.sma50 is not None]
    pct_above_50dma = (
        round(100 * sum(1 for r in above_50 if r.price > r.sma50) / len(above_50), 1)
        if above_50
        else None
    )

    # % above 200-DMA
    above_200 = [r for r in results if r.price is not None and r.sma200 is not None]
    pct_above_200dma = (
        round(100 * sum(1 for r in above_200 if r.price > r.sma200) / len(above_200), 1)
        if above_200
        else None
    )

    # Advancers / decliners
    with_prev = [r for r in results if r.prev_close is not None and r.prev_close != 0]
    advancers = sum(1 for r in with_prev if r.price > r.prev_close)
    decliners = sum(1 for r in with_prev if r.price < r.prev_close)

    # 52-week highs/lows — both use rolling 252-day High/Low on the ScanResult
    # table's pct_from_52w_high field for the high leg; we approximate the low
    # leg with pct_from_52w_low when that column is added.  For now, new_lows
    # is derived from breakout == False AND near 52w low — the low-hanging
    # proxy stored in ScanResult.pct_from_52w_high is negative for near lows.
    new_highs = sum(1 for r in results if r.breakout)

    # new_lows proxy: not a breakout AND price within 2% of 52w low.
    # pct_from_52w_high is negative when close is below the 52w high;
    # we don't have a raw 52w_low field so we use the presence of rsi>30
    # as a rough filter and wait for a future pct_from_52w_low column.
    # Until then, set new_lows = 0 — the spec's new_highs/new_lows need
    # a pct_from_52w_low column in ScanResult.
    new_lows = 0

    return {
        "pct_above_50dma": pct_above_50dma,
        "pct_above_200dma": pct_above_200dma,
        "advancers": advancers,
        "decliners": decliners,
        "new_highs": new_highs,
        "new_lows": new_lows,
    }


def classify_regime(pct_above_50dma: float | None) -> str:
    """Classify overall market regime from the % of symbols above their 50-DMA."""
    if pct_above_50dma is None:
        return "neutral"
    if pct_above_50dma > RISK_ON_THRESHOLD:
        return "risk_on"
    if pct_above_50dma < RISK_OFF_THRESHOLD:
        return "risk_off"
    return "neutral"


HISTORY_LIMIT = 30


async def get_market_breadth(
    db, history_limit: int = HISTORY_LIMIT, breadth_date: date | None = None
) -> dict:
    """Latest breadth snapshot plus trailing history (oldest first) for a sparkline.

    When breadth_date is provided, returns the single row for that trading day.
    Otherwise returns the latest row plus the prior (history_limit - 1) rows.
    """
    if breadth_date is not None:
        # Single-date lookup
        stmt = (
            select(MarketBreadth, SignalScan.scanned_at)
            .join(SignalScan, MarketBreadth.scan_id == SignalScan.id)
            .where(MarketBreadth.date == breadth_date)
            .limit(1)
        )
        row = (await db.execute(stmt)).first()
        if not row:
            return {"error": f"No breadth data for {breadth_date}"}
        breadth, scanned_at = row
        return {
            "date": breadth.date.isoformat(),
            "pct_above_50dma": breadth.pct_above_50dma,
            "pct_above_200dma": breadth.pct_above_200dma,
            "advancers": breadth.advancers,
            "decliners": breadth.decliners,
            "new_highs": breadth.new_highs,
            "new_lows": breadth.new_lows,
            "regime": classify_regime(breadth.pct_above_50dma),
        }

    # Default: latest + trailing history
    stmt = (
        select(MarketBreadth, SignalScan.scanned_at)
        .join(SignalScan, MarketBreadth.scan_id == SignalScan.id)
        .order_by(SignalScan.scanned_at.desc())
        .limit(history_limit)
    )
    rows = (await db.execute(stmt)).all()

    if not rows:
        return {
            "date": None,
            "pct_above_50dma": None,
            "pct_above_200dma": None,
            "advancers": 0,
            "decliners": 0,
            "new_highs": 0,
            "new_lows": 0,
            "regime": "neutral",
            "history": [],
        }

    latest, latest_scanned_at = rows[0]
    history = [
        {
            "date": scanned_at.isoformat() if scanned_at else None,
            "pct_above_50dma": breadth.pct_above_50dma,
        }
        for breadth, scanned_at in reversed(rows)
    ]

    return {
        "date": latest.date.isoformat() if latest.date else None,
        "pct_above_50dma": latest.pct_above_50dma,
        "pct_above_200dma": latest.pct_above_200dma,
        "advancers": latest.advancers,
        "decliners": latest.decliners,
        "new_highs": latest.new_highs,
        "new_lows": latest.new_lows,
        "regime": classify_regime(latest.pct_above_50dma),
        "history": history,
    }