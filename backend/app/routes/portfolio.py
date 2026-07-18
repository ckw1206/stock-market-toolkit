"""Holdings ledger API. Pure ledger: every response derives state on read.

Consistency issues are payload warnings, never HTTP errors (spec:
warn-but-allow). Malformed entries fail Pydantic validation -> 422.
"""
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.portfolio import PortfolioSuggestionDismissal, PortfolioTransaction
from app.models.user import User
from app.schemas.portfolio import (
    SuggestionAccept,
    SuggestionDismiss,
    SuggestionsOut,
    SummaryOut,
    TransactionCreate,
    TransactionOut,
    TransactionWithWarnings,
    WarningsOut,
    derive_currency,
)
from app.services.portfolio_ledger import (
    build_summary,
    load_transactions,
    replay,
    warnings_payload,
)
from app.services.portfolio_suggestions import build_suggestions

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _model_fields(body: TransactionCreate) -> dict:
    """Schema -> model kwargs; Decimals stored as strings (see models)."""
    return {
        "type": body.type,
        "trade_date": body.trade_date,
        "symbol": body.symbol,
        "qty": str(body.qty) if body.qty is not None else None,
        "price": str(body.price) if body.price is not None else None,
        "amount": str(body.amount) if body.amount is not None else None,
        "fee": str(body.fee),
        "currency": body.currency,
        "note": body.note,
    }


async def _current_warnings(db: AsyncSession, user_id: str) -> list[dict]:
    return warnings_payload(replay(await load_transactions(db, user_id)))


async def _get_owned(db: AsyncSession, user_id: str, txn_id: int) -> PortfolioTransaction:
    txn = await db.get(PortfolioTransaction, txn_id)
    if txn is None or txn.user_id != user_id:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return txn


@router.get("/transactions", response_model=list[TransactionOut])
async def list_transactions(
    symbol: str | None = Query(None),
    type: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(PortfolioTransaction).where(
        PortfolioTransaction.user_id == current_user.id
    )
    if symbol:
        stmt = stmt.where(PortfolioTransaction.symbol == symbol.strip().upper())
    if type:
        stmt = stmt.where(PortfolioTransaction.type == type)
    stmt = stmt.order_by(
        PortfolioTransaction.trade_date.desc(), PortfolioTransaction.id.desc()
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("/transactions", response_model=TransactionWithWarnings, status_code=201)
async def create_transaction(
    body: TransactionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    txn = PortfolioTransaction(user_id=current_user.id, **_model_fields(body))
    db.add(txn)
    await db.commit()
    await db.refresh(txn)
    return {"transaction": txn,
            "warnings": await _current_warnings(db, current_user.id)}


@router.put("/transactions/{txn_id}", response_model=TransactionWithWarnings)
async def update_transaction(
    body: TransactionCreate,
    txn_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    txn = await _get_owned(db, current_user.id, txn_id)
    for key, value in _model_fields(body).items():
        setattr(txn, key, value)
    await db.commit()
    await db.refresh(txn)
    return {"transaction": txn,
            "warnings": await _current_warnings(db, current_user.id)}


@router.delete("/transactions/{txn_id}", response_model=WarningsOut)
async def delete_transaction(
    txn_id: int = Path(..., gt=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    txn = await _get_owned(db, current_user.id, txn_id)
    await db.delete(txn)
    await db.commit()
    return {"warnings": await _current_warnings(db, current_user.id)}


@router.get("/summary", response_model=SummaryOut)
async def get_summary(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await build_summary(db, current_user.id)


async def _ensure_dismissal(
    db: AsyncSession, user_id: str, symbol: str, type_: str, ex_date
) -> None:
    result = await db.execute(
        select(PortfolioSuggestionDismissal).where(
            PortfolioSuggestionDismissal.user_id == user_id,
            PortfolioSuggestionDismissal.symbol == symbol,
            PortfolioSuggestionDismissal.type == type_,
            PortfolioSuggestionDismissal.ex_date == ex_date,
        )
    )
    if result.scalars().first() is None:
        db.add(PortfolioSuggestionDismissal(
            user_id=user_id, symbol=symbol, type=type_, ex_date=ex_date))


@router.get("/suggestions", response_model=SuggestionsOut)
async def get_suggestions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await build_suggestions(db, current_user.id)


@router.post("/suggestions/accept", response_model=TransactionWithWarnings,
             status_code=201)
async def accept_suggestion(
    body: SuggestionAccept,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.type == "dividend":
        create = TransactionCreate(
            type="dividend", trade_date=body.ex_date, symbol=body.symbol,
            amount=body.amount, note=body.note,
            currency=derive_currency(body.symbol),
        )
    else:
        create = TransactionCreate(
            type="split", trade_date=body.ex_date, symbol=body.symbol,
            qty=body.ratio, note=body.note,
            currency=derive_currency(body.symbol),
        )
    txn = PortfolioTransaction(user_id=current_user.id, **_model_fields(create))
    db.add(txn)
    await _ensure_dismissal(db, current_user.id, body.symbol, body.type, body.ex_date)
    await db.commit()
    await db.refresh(txn)
    return {"transaction": txn,
            "warnings": await _current_warnings(db, current_user.id)}


@router.post("/suggestions/dismiss")
async def dismiss_suggestion(
    body: SuggestionDismiss,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await _ensure_dismissal(db, current_user.id, body.symbol, body.type, body.ex_date)
    await db.commit()
    return {"ok": True}