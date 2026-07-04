"""Market breadth — aggregate market-wide stats over a scan's universe.

Gives users the "market weather" before acting on any individual signal: a
BUY signal in a broadly deteriorating market deserves different treatment
than one in a strong tape.
"""

from typing import Sequence

from sqlalchemy import select

from app.models import ScanResult, MarketBreadth, SignalScan

RISK_ON_THRESHOLD = 60.0
RISK_OFF_THRESHOLD = 40.0


def compute_breadth(results: Sequence[ScanResult]) -> dict:
    """Aggregate per-symbol scan results into market-wide breadth stats.

    - pct_above_sma50: % of symbols whose price is above their 50-day SMA
    - advancers/decliners: symbols with a positive/negative day's % change
    - new_highs: symbols flagged as a 52-week breakout by the signal engine

    Symbols missing the relevant field are excluded from that leg's
    denominator rather than counted as a miss.
    """
    total = len(results)
    if total == 0:
        return {
            "total_symbols": 0,
            "pct_above_sma50": None,
            "advancers": 0,
            "decliners": 0,
            "new_highs": 0,
        }

    above_sma50 = [
        r for r in results if r.price is not None and r.sma50 is not None
    ]
    pct_above_sma50 = (
        round(100 * sum(1 for r in above_sma50 if r.price > r.sma50) / len(above_sma50), 1)
        if above_sma50
        else None
    )

    advancers = sum(1 for r in results if r.pct_change_1d is not None and r.pct_change_1d > 0)
    decliners = sum(1 for r in results if r.pct_change_1d is not None and r.pct_change_1d < 0)
    new_highs = sum(1 for r in results if r.breakout)

    return {
        "total_symbols": total,
        "pct_above_sma50": pct_above_sma50,
        "advancers": advancers,
        "decliners": decliners,
        "new_highs": new_highs,
    }


def classify_regime(pct_above_sma50: float | None) -> str:
    """Classify overall market regime from the % of symbols above their 50-DMA."""
    if pct_above_sma50 is None:
        return "neutral"
    if pct_above_sma50 > RISK_ON_THRESHOLD:
        return "risk_on"
    if pct_above_sma50 < RISK_OFF_THRESHOLD:
        return "risk_off"
    return "neutral"


HISTORY_LIMIT = 30


async def get_market_breadth(db, history_limit: int = HISTORY_LIMIT) -> dict:
    """Latest breadth snapshot plus trailing history (oldest first) for a sparkline."""
    stmt = (
        select(MarketBreadth, SignalScan.scanned_at)
        .join(SignalScan, MarketBreadth.scan_id == SignalScan.id)
        .order_by(SignalScan.scanned_at.desc())
        .limit(history_limit)
    )
    rows = (await db.execute(stmt)).all()

    if not rows:
        return {
            "scanned_at": None,
            "total_symbols": 0,
            "pct_above_sma50": None,
            "advancers": 0,
            "decliners": 0,
            "new_highs": 0,
            "regime": "neutral",
            "history": [],
        }

    latest, latest_scanned_at = rows[0]
    history = [
        {
            "date": scanned_at.isoformat() if scanned_at else None,
            "pct_above_sma50": breadth.pct_above_sma50,
        }
        for breadth, scanned_at in reversed(rows)
    ]

    return {
        "scanned_at": latest_scanned_at.isoformat() if latest_scanned_at else None,
        "total_symbols": latest.total_symbols,
        "pct_above_sma50": latest.pct_above_sma50,
        "advancers": latest.advancers,
        "decliners": latest.decliners,
        "new_highs": latest.new_highs,
        "regime": classify_regime(latest.pct_above_sma50),
        "history": history,
    }
