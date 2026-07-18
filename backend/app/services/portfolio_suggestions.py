"""Corporate-action suggestions: computed on request, never stored.

For every symbol the user ever traded, diff Yahoo's dividend/split history
against the ledger; emit a suggestion for each action where shares were held
on the ex-date and there is no matching ledger entry and no dismissal.
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.portfolio import PortfolioSuggestionDismissal
from app.providers import fundamentals_provider
from app.schemas.portfolio import derive_currency
from app.services.portfolio_ledger import load_transactions, shares_on


async def build_suggestions(db: AsyncSession, user_id: str) -> dict:
    txns = await load_transactions(db, user_id)
    symbols = sorted({t.symbol for t in txns if t.symbol})
    existing = {(t.symbol, t.type, t.trade_date) for t in txns}

    result = await db.execute(
        select(PortfolioSuggestionDismissal).where(
            PortfolioSuggestionDismissal.user_id == user_id
        )
    )
    dismissed = {(d.symbol, d.type, d.ex_date) for d in result.scalars()}

    suggestions: list[dict] = []
    degraded_symbols: list[str] = []

    for symbol in symbols:
        try:
            dividends = await fundamentals_provider.get_dividends(symbol)
            splits = await fundamentals_provider.get_splits(symbol)
        except Exception:
            degraded_symbols.append(symbol)
            continue

        for ts, per_share in dividends.items():
            ex_date = ts.date()
            if (symbol, "dividend", ex_date) in existing:
                continue
            if (symbol, "dividend", ex_date) in dismissed:
                continue
            shares = shares_on(txns, symbol, ex_date)
            if shares <= 0:
                continue
            per = Decimal(str(per_share))
            suggestions.append({
                "symbol": symbol, "type": "dividend", "ex_date": ex_date,
                "shares": shares, "per_share": per, "gross_amount": shares * per,
                "ratio": None, "currency": derive_currency(symbol),
            })

        for ts, ratio in splits.items():
            ex_date = ts.date()
            if (symbol, "split", ex_date) in existing:
                continue
            if (symbol, "split", ex_date) in dismissed:
                continue
            shares = shares_on(txns, symbol, ex_date)
            if shares <= 0:
                continue
            suggestions.append({
                "symbol": symbol, "type": "split", "ex_date": ex_date,
                "shares": shares, "per_share": None, "gross_amount": None,
                "ratio": Decimal(str(ratio)), "currency": derive_currency(symbol),
            })

    suggestions.sort(key=lambda s: (s["ex_date"], s["symbol"]), reverse=True)
    return {"suggestions": suggestions, "degraded": bool(degraded_symbols),
            "degraded_symbols": degraded_symbols}