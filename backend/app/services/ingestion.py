"""Nightly batch ingestion service for fundamentals data."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import AsyncSessionLocal
from app.models import (
    Dividend,
    FinancialStatement,
    JobRun,
    SymbolScore,
)
from app.providers import fundamentals_provider
from app.services.scoring import (
    dividend_quality,
    piotroski_f_score,
    profitability_metrics,
)
from app.services.universe import get_tracked_universe

log = logging.getLogger(__name__)


def _now():
    return datetime.now(timezone.utc)


async def upsert_financial_statement(
    db: AsyncSession, symbol: str, period: str, data: dict
) -> FinancialStatement:
    stmt = select(FinancialStatement).where(
        FinancialStatement.symbol == symbol,
        FinancialStatement.period == period,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        existing.data = data
        existing.fetched_at = _now()
        return existing
    row = FinancialStatement(
        symbol=symbol,
        period=period,
        data=data,
        fetched_at=_now(),
    )
    db.add(row)
    return row


async def upsert_dividends(
    db: AsyncSession, symbol: str, dividends_df
) -> list[Dividend]:
    rows = []
    if dividends_df is None or dividends_df.empty:
        return rows
    for ex_date, amount in dividends_df.items():
        if isinstance(ex_date, str):
            ex_date = datetime.fromisoformat(ex_date)
        stmt = select(Dividend).where(
            Dividend.symbol == symbol,
            Dividend.ex_date == ex_date,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            existing.amount = float(amount)
            existing.fetched_at = _now()
            rows.append(existing)
        else:
            row = Dividend(
                symbol=symbol,
                amount=float(amount),
                ex_date=ex_date,
                fetched_at=_now(),
            )
            db.add(row)
            rows.append(row)
    return rows


async def upsert_symbol_score(
    db: AsyncSession,
    symbol: str,
    score_type: str,
    score: Optional[float],
    details: Optional[dict],
) -> SymbolScore:
    stmt = select(SymbolScore).where(
        SymbolScore.symbol == symbol,
        SymbolScore.score_type == score_type,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        existing.score = score
        existing.details = details
        existing.calculated_at = _now()
        return existing
    row = SymbolScore(
        symbol=symbol,
        score_type=score_type,
        score=score,
        details=details,
        calculated_at=_now(),
    )
    db.add(row)
    return row


async def run_nightly_ingest(job_run_id: Optional[int] = None) -> int:
    settings = get_settings()
    symbols = get_tracked_universe()
    max_symbols = min(settings.INGEST_MAX_SYMBOLS, len(symbols))
    symbols = symbols[:max_symbols]
    delay = settings.INGEST_DELAY_SECONDS
    symbols_processed = 0
    total_errors = 0

    if job_run_id is not None:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(JobRun)
                .where(JobRun.id == job_run_id)
                .values(total_symbols=len(symbols))
            )
            await db.commit()

    for symbol in symbols:
        try:
            async with AsyncSessionLocal() as db:
                data = await fundamentals_provider.get_fundamentals_dict(symbol)
                cur = data.get("current", {})
                prev = data.get("prior", {})

                await upsert_financial_statement(
                    db, symbol, "annual", {"current": cur, "prior": prev}
                )

                div_df = await fundamentals_provider.get_dividends(symbol)
                await upsert_dividends(db, symbol, div_df)

                p_score = piotroski_f_score(cur, prev)
                await upsert_symbol_score(db, symbol, "piotroski", p_score, None)

                p_metrics = profitability_metrics(cur, prev)
                await upsert_symbol_score(db, symbol, "profitability", None, p_metrics)

                dq = dividend_quality(cur, prev, div_df)
                await upsert_symbol_score(
                    db, symbol, "dividend_quality", dq["score"], dq["details"]
                )

                await db.commit()
                symbols_processed += 1
        except Exception as e:
            log.error("Failed to ingest %s: %s", symbol, e)
            total_errors += 1

        if delay > 0:
            await asyncio.sleep(delay)

    if job_run_id is not None:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(JobRun)
                .where(JobRun.id == job_run_id)
                .values(
                    status="completed",
                    symbols_processed=symbols_processed,
                    errors=total_errors,
                    completed_at=_now(),
                )
            )
            await db.commit()

    log.info(
        "Nightly ingest complete: %d/%d symbols processed, %d errors",
        symbols_processed,
        len(symbols),
        total_errors,
    )
    return symbols_processed


async def get_latest_job_run(db: AsyncSession) -> Optional[JobRun]:
    result = await db.execute(
        select(JobRun)
        .where(JobRun.job_type == "nightly_ingest")
        .order_by(JobRun.started_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()
