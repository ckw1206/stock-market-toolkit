"""Nightly signal scan service."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import SignalScan, ScanResult, MarketBreadth
from app.services.signals import (
    compute_analysis_impl,
    ProviderUnavailableError,
    NoDataError,
    ThinHistoryError,
)
from app.services.market_breadth import compute_breadth
from app.services.universe import get_scan_universe
from app.services.cache import cached, cache_key

log = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc)


async def get_sector(symbol: str) -> Optional[str]:
    """Fetch a symbol's sector via the provider info call, cached for a day.

    Returns None on any failure — the scan must never break on enrichment.
    """
    from app.providers import market_provider

    async def _load():
        info = await market_provider.get_info(symbol.upper())
        value = info.value if hasattr(info, "value") else info
        return (value or {}).get("sector")

    try:
        return await cached(cache_key("sector", symbol.upper()), ttl=86400, loader=_load)
    except Exception as exc:
        log.warning("Sector lookup failed for %s: %s", symbol, exc)
        return None


async def compute_signal_for_symbol(symbol: str, period: str = "3mo") -> Optional[dict]:
    """Compute signal for a symbol, returning None on any failure (log + skip)."""
    try:
        return await compute_analysis_impl(symbol, period)
    except (ProviderUnavailableError, NoDataError, ThinHistoryError) as exc:
        log.warning("Signal scan skipped for %s: %s", symbol, exc)
        return None
    except Exception as exc:
        log.error("Unexpected error computing signal for %s: %s", symbol, exc)
        return None


async def run_signal_scan(job_run_id: Optional[int] = None) -> dict:
    settings = get_settings()
    delay = settings.INGEST_DELAY_SECONDS

    async with AsyncSessionLocal() as db:
        universe = await get_scan_universe(db)

    total_symbols = len(universe)
    symbols_processed = 0
    errors = 0

    scan = SignalScan(job_run_id=job_run_id)
    results = []

    for symbol in universe:
        signal_data = None
        try:
            signal_data = await compute_signal_for_symbol(symbol, period="3mo")
        except Exception as exc:
            log.error("Failed to compute signal for %s: %s", symbol, exc)
            errors += 1

        if signal_data:
            indicators = signal_data["indicators"]
            result = ScanResult(
                scan=scan,
                symbol=signal_data["symbol"],
                signal=signal_data["signal"],
                score=signal_data["score"],
                confidence=signal_data["confidence"],
                price=signal_data["price"],
                rvol=indicators.get("rvol"),
                breakout=signal_data["breakout"],
                volume_spike=signal_data["volume_spike"],
                reasons=signal_data["reasons"],
                rsi=indicators.get("rsi"),
                sma20=indicators.get("sma20"),
                sma50=indicators.get("sma50"),
                sma200=indicators.get("sma200"),
                prev_close=indicators.get("prev_close"),
                volume_ratio=indicators.get("volume_ratio"),
                pct_from_52w_high=indicators.get("pct_from_52w_high"),
                pct_change_1d=indicators.get("pct_change_1d"),
                sector=await get_sector(symbol),
            )
            results.append(result)
            symbols_processed += 1

        if delay > 0:
            await asyncio.sleep(delay)

    buys = [r for r in results if r.signal == "BUY"]
    sells = [r for r in results if r.signal == "SELL"]

    buys.sort(key=lambda r: r.score, reverse=True)
    sells.sort(key=lambda r: r.score)

    for rank, r in enumerate(buys, 1):
        r.rank = rank
    for rank, r in enumerate(sells, 1):
        r.rank = rank

    breadth_stats = compute_breadth(results)

    # Use today's UTC date as the breadth row's trading date.
    # For a nightly scan run after US market close (~9pm UTC) this matches
    # the just-closed trading day. Using date rather than scan_id as the pk
    # enforces one breadth row per trading day (idempotent upsert semantics).
    scan_date = _now().date()

    async with AsyncSessionLocal() as db:
        scan.results = results
        db.add(scan)
        await db.flush()  # get scan.id
        db.add(MarketBreadth(date=scan_date, scan_id=scan.id, **breadth_stats))
        await db.commit()
        scan_id = scan.id

    log.info(
        "Signal scan complete: %d/%d symbols processed, %d errors, scan_id=%d",
        symbols_processed,
        total_symbols,
        errors,
        scan_id,
    )

    return {
        "scan_id": scan_id,
        "symbols_processed": symbols_processed,
        "total_symbols": total_symbols,
        "errors": errors,
        "buys": len(buys),
        "sells": len(sells),
    }


async def get_latest_scan(db) -> Optional[SignalScan]:
    from sqlalchemy import select

    result = await db.execute(
        select(SignalScan).order_by(SignalScan.scanned_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def get_top_signals(db, limit: int = 10) -> dict:
    scan = await get_latest_scan(db)
    if scan is None:
        return {"scanned_at": None, "buys": [], "sells": []}

    from sqlalchemy import select

    result = await db.execute(
        select(ScanResult)
        .where(ScanResult.scan_id == scan.id)
        .order_by(ScanResult.signal, ScanResult.rank)
    )
    all_results = result.scalars().all()

    buys = [r for r in all_results if r.signal == "BUY"][:limit]
    sells = [r for r in all_results if r.signal == "SELL"][:limit]

    def _result_to_dict(r: ScanResult) -> dict:
        return {
            "symbol": r.symbol,
            "signal": r.signal,
            "confidence": r.confidence,
            "price": r.price,
            "rvol": r.rvol,
            "breakout": r.breakout,
            "volume_spike": r.volume_spike,
            "reasons": r.reasons or [],
            "rank": r.rank,
        }

    return {
        "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
        "buys": [_result_to_dict(r) for r in buys],
        "sells": [_result_to_dict(r) for r in sells],
    }