"""Screener and sector heatmap over the latest signal scan."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select

from app.auth import get_current_user
from app.database import AsyncSessionLocal
from app.models import User, ScanResult
from app.services.top_signals import get_latest_scan

router = APIRouter(prefix="/api", tags=["screener"])

SORT_COLUMNS = {
    "score": ScanResult.score,
    "rvol": ScanResult.rvol,
    "rsi": ScanResult.rsi,
    "pct_from_52w_high": ScanResult.pct_from_52w_high,
    "pct_change_1d": ScanResult.pct_change_1d,
    "price": ScanResult.price,
}


def _result_to_dict(r: ScanResult) -> dict:
    return {
        "symbol": r.symbol,
        "signal": r.signal,
        "score": r.score,
        "confidence": r.confidence,
        "price": r.price,
        "rvol": r.rvol,
        "breakout": r.breakout,
        "volume_spike": r.volume_spike,
        "rsi": r.rsi,
        "sma20": r.sma20,
        "sma50": r.sma50,
        "volume_ratio": r.volume_ratio,
        "pct_from_52w_high": r.pct_from_52w_high,
        "pct_change_1d": r.pct_change_1d,
        "sector": r.sector,
        "rank": r.rank,
    }


@router.get("/screener")
async def screen(
    signal: str | None = Query(None, pattern="^(BUY|SELL|NEUTRAL)$"),
    rsi_min: float | None = Query(None, ge=0, le=100),
    rsi_max: float | None = Query(None, ge=0, le=100),
    rvol_min: float | None = Query(None, ge=0),
    breakout: bool | None = Query(None),
    price_min: float | None = Query(None, ge=0),
    price_max: float | None = Query(None, ge=0),
    pct_from_52w_high_min: float | None = Query(None),
    above_sma50: bool | None = Query(None),
    sector: str | None = Query(None),
    sort: str = Query("score"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    """Filter the latest scan's results with SQL-level criteria (AND-combined)."""
    if sort not in SORT_COLUMNS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid sort '{sort}'; must be one of {sorted(SORT_COLUMNS)}",
        )

    async with AsyncSessionLocal() as db:
        scan = await get_latest_scan(db)
        if scan is None:
            return {"scanned_at": None, "count": 0, "results": []}

        stmt = select(ScanResult).where(ScanResult.scan_id == scan.id)
        if signal is not None:
            stmt = stmt.where(ScanResult.signal == signal)
        if rsi_min is not None:
            stmt = stmt.where(ScanResult.rsi >= rsi_min)
        if rsi_max is not None:
            stmt = stmt.where(ScanResult.rsi <= rsi_max)
        if rvol_min is not None:
            stmt = stmt.where(ScanResult.rvol >= rvol_min)
        if breakout is not None:
            stmt = stmt.where(ScanResult.breakout.is_(breakout))
        if price_min is not None:
            stmt = stmt.where(ScanResult.price >= price_min)
        if price_max is not None:
            stmt = stmt.where(ScanResult.price <= price_max)
        if pct_from_52w_high_min is not None:
            stmt = stmt.where(ScanResult.pct_from_52w_high >= pct_from_52w_high_min)
        if above_sma50 is not None:
            cond = ScanResult.price > ScanResult.sma50
            stmt = stmt.where(cond if above_sma50 else ~cond)
        if sector is not None:
            stmt = stmt.where(ScanResult.sector == sector)

        col = SORT_COLUMNS[sort]
        stmt = stmt.order_by(col.desc() if order == "desc" else col.asc()).limit(limit)

        rows = (await db.execute(stmt)).scalars().all()

    return {
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "count": len(rows),
        "results": [_result_to_dict(r) for r in rows],
    }


@router.get("/heatmap")
async def heatmap(current_user: User = Depends(get_current_user)):
    """Latest scan grouped by sector for the heatmap widget."""
    async with AsyncSessionLocal() as db:
        scan = await get_latest_scan(db)
        if scan is None:
            return {"scanned_at": None, "sectors": []}

        rows = (
            (
                await db.execute(
                    select(ScanResult).where(ScanResult.scan_id == scan.id)
                )
            )
            .scalars()
            .all()
        )

    groups: dict[str, list[dict]] = {}
    for r in rows:
        key = r.sector or "Other"
        groups.setdefault(key, []).append(
            {
                "symbol": r.symbol,
                "pct_change_1d": r.pct_change_1d,
                "price": r.price,
                "signal": r.signal,
                "rvol": r.rvol,
            }
        )

    # Named sectors alphabetically, "Other" last; tiles by |move| descending
    sectors = [
        {
            "sector": name,
            "symbols": sorted(
                syms, key=lambda s: abs(s["pct_change_1d"] or 0), reverse=True
            ),
        }
        for name, syms in sorted(
            groups.items(), key=lambda kv: (kv[0] == "Other", kv[0])
        )
    ]

    return {
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "sectors": sectors,
    }
