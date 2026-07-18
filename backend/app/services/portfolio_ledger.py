"""Holdings ledger replay: pure fold over the user's transaction history.

The DB stores only transactions; positions, average cost, cash, realized
P&L, and warnings are all derived here on every read, so edits/backdates/
deletes can never leave stale state. Numeric columns arrive as strings
(see models/portfolio.py) — everything is converted to Decimal at entry.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

ZERO = Decimal("0")


def _d(value) -> Decimal | None:
    if value is None:
        return None
    return value if isinstance(value, Decimal) else Decimal(str(value))


@dataclass
class Position:
    qty: Decimal = ZERO
    avg_cost: Decimal | None = None
    realized_pnl: Decimal = ZERO
    dividends: Decimal = ZERO
    currency: str = "USD"


@dataclass
class LedgerWarning:
    kind: str
    trade_date: date
    transaction_id: int
    symbol: str | None = None
    currency: str | None = None
    message: str = ""


@dataclass
class LedgerState:
    cash: dict[str, Decimal] = field(default_factory=dict)
    positions: dict[str, Position] = field(default_factory=dict)
    warnings: list[LedgerWarning] = field(default_factory=list)


def sort_key(txn) -> tuple:
    return (txn.trade_date, 1 if txn.type == "adjust" else 0, txn.id)


_CASH_TYPES = ("buy", "sell", "dividend", "deposit", "withdrawal")


def replay(transactions) -> LedgerState:
    state = LedgerState()
    raw: list[tuple[str, int, LedgerWarning]] = []
    last_adjust: dict[str, int] = {}

    for order, txn in enumerate(sorted(transactions, key=sort_key)):
        t = txn.type
        qty, price = _d(txn.qty), _d(txn.price)
        amount, fee = _d(txn.amount), _d(txn.fee) or ZERO
        cur = txn.currency
        pos: Position | None = None

        if txn.symbol is not None:
            pos = state.positions.setdefault(txn.symbol, Position(currency=cur))
            if pos.currency != cur:
                raw.append((f"sym:{txn.symbol}", order, LedgerWarning(
                    kind="mixed_currency", trade_date=txn.trade_date,
                    transaction_id=txn.id, symbol=txn.symbol, currency=cur,
                    message=f"{txn.symbol} has entries in more than one currency",
                )))
            pos.currency = cur

        if t == "buy":
            cost = qty * price + fee
            if pos.qty <= ZERO or pos.avg_cost is None:
                pos.avg_cost = cost / qty
            else:
                pos.avg_cost = (pos.qty * pos.avg_cost + cost) / (pos.qty + qty)
            pos.qty += qty
            state.cash[cur] = state.cash.get(cur, ZERO) - cost
        elif t == "sell":
            basis = pos.avg_cost if pos.avg_cost is not None else ZERO
            pos.realized_pnl += qty * (price - basis) - fee
            pos.qty -= qty
            state.cash[cur] = state.cash.get(cur, ZERO) + qty * price - fee
        elif t == "dividend":
            pos.dividends += amount
            state.cash[cur] = state.cash.get(cur, ZERO) + amount
        elif t == "deposit":
            state.cash[cur] = state.cash.get(cur, ZERO) + amount
        elif t == "withdrawal":
            state.cash[cur] = state.cash.get(cur, ZERO) - amount
        elif t == "split":
            pos.qty *= qty
            if pos.avg_cost is not None:
                pos.avg_cost /= qty
        elif t == "adjust":
            if txn.symbol is not None:
                pos.qty = qty
                pos.avg_cost = price if qty > ZERO else None
                pos.realized_pnl = ZERO
                pos.dividends = ZERO
                last_adjust[f"sym:{txn.symbol}"] = order
            else:
                state.cash[cur] = amount
                last_adjust[f"cash:{cur}"] = order

        if pos is not None and pos.qty == ZERO:
            pos.avg_cost = None

        if pos is not None and pos.qty < ZERO:
            raw.append((f"sym:{txn.symbol}", order, LedgerWarning(
                kind="negative_position", trade_date=txn.trade_date,
                transaction_id=txn.id, symbol=txn.symbol,
                message=f"{txn.symbol} position is {pos.qty} after this entry",
            )))
        if t in _CASH_TYPES and state.cash.get(cur, ZERO) < ZERO:
            raw.append((f"cash:{cur}", order, LedgerWarning(
                kind="negative_cash", trade_date=txn.trade_date,
                transaction_id=txn.id, currency=cur,
                message=f"{cur} cash is {state.cash[cur]} after this entry",
            )))

    state.warnings = [w for scope, o, w in raw if o > last_adjust.get(scope, -1)]
    return state