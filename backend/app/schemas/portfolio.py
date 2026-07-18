# backend/app/schemas/portfolio.py
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

TransactionType = Literal[
    "buy", "sell", "dividend", "deposit", "withdrawal", "split", "adjust"
]
Currency = Literal["USD", "TWD"]


def derive_currency(symbol: str) -> str:
    s = symbol.strip().upper()
    return "TWD" if s.endswith(".TW") or s.endswith(".TWO") else "USD"


class TransactionCreate(BaseModel):
    type: TransactionType
    trade_date: date
    symbol: str | None = Field(None, min_length=1, max_length=20)
    qty: Decimal | None = Field(None, ge=0)
    price: Decimal | None = Field(None, ge=0)
    amount: Decimal | None = None
    fee: Decimal = Field(Decimal("0"), ge=0)
    currency: Currency | None = None
    note: str | None = Field(None, max_length=500)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str | None) -> str | None:
        return v.strip().upper() if v else v

    @model_validator(mode="after")
    def check_fields_for_type(self) -> "TransactionCreate":
        def need(cond: bool, msg: str) -> None:
            if not cond:
                raise ValueError(msg)

        t = self.type
        if t in ("buy", "sell"):
            need(bool(self.symbol), f"{t} requires symbol")
            need(self.qty is not None and self.qty > 0, f"{t} requires qty > 0")
            need(self.price is not None, f"{t} requires price")
            need(self.amount is None, f"{t} forbids amount")
        elif t == "dividend":
            need(bool(self.symbol), "dividend requires symbol")
            need(self.amount is not None and self.amount >= 0,
                 "dividend requires amount >= 0")
            need(self.qty is None and self.price is None, "dividend forbids qty/price")
        elif t in ("deposit", "withdrawal"):
            need(self.amount is not None and self.amount > 0,
                 f"{t} requires amount > 0")
            need(self.symbol is None and self.qty is None and self.price is None,
                 f"{t} forbids symbol/qty/price")
        elif t == "split":
            need(bool(self.symbol), "split requires symbol")
            need(self.qty is not None and self.qty > 0,
                 "split requires qty (the ratio, e.g. 4 for a 4-for-1)")
            need(self.price is None and self.amount is None,
                 "split forbids price/amount")
        elif t == "adjust":
            if self.symbol is not None:  # position variant
                need(self.qty is not None, "adjust (position) requires qty")
                need(self.price is not None, "adjust (position) requires price")
                need(self.amount is None, "adjust (position) forbids amount")
            else:  # cash variant
                need(self.amount is not None, "adjust (cash) requires amount")
                need(self.qty is None and self.price is None,
                     "adjust (cash) forbids qty/price")

        if self.currency is None:
            if self.symbol is not None:
                self.currency = derive_currency(self.symbol)  # type: ignore[assignment]
            else:
                raise ValueError("cash-only entries require currency")
        return self


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    trade_date: date
    symbol: str | None
    qty: Decimal | None
    price: Decimal | None
    amount: Decimal | None
    fee: Decimal
    currency: str
    note: str | None
    created_at: datetime
    updated_at: datetime


class LedgerWarningOut(BaseModel):
    kind: Literal["negative_position", "negative_cash", "mixed_currency"]
    trade_date: date
    transaction_id: int
    symbol: str | None = None
    currency: str | None = None
    message: str


class TransactionWithWarnings(BaseModel):
    transaction: TransactionOut
    warnings: list[LedgerWarningOut]


class WarningsOut(BaseModel):
    warnings: list[LedgerWarningOut]


class HoldingOut(BaseModel):
    symbol: str
    currency: str
    qty: Decimal
    avg_cost: Decimal | None
    price: Decimal | None
    market_value: Decimal | None
    unrealized_pnl: Decimal | None
    realized_pnl: Decimal
    dividends: Decimal


class CurrencyTotalsOut(BaseModel):
    cash: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal
    dividends: Decimal
    market_value_complete: bool


class SummaryOut(BaseModel):
    currencies: dict[str, CurrencyTotalsOut]
    holdings: list[HoldingOut]
    warnings: list[LedgerWarningOut]


class SuggestionOut(BaseModel):
    symbol: str
    type: Literal["dividend", "split"]
    ex_date: date
    shares: Decimal
    per_share: Decimal | None = None     # dividend only
    gross_amount: Decimal | None = None  # dividend only: shares * per_share
    ratio: Decimal | None = None         # split only
    currency: str


class SuggestionsOut(BaseModel):
    suggestions: list[SuggestionOut]
    degraded: bool
    degraded_symbols: list[str]


class SuggestionAccept(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    type: Literal["dividend", "split"]
    ex_date: date
    amount: Decimal | None = None  # dividend: final (net) cash received — editable
    ratio: Decimal | None = None   # split ratio
    note: str | None = Field(None, max_length=500)

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.strip().upper()

    @model_validator(mode="after")
    def check_variant(self) -> "SuggestionAccept":
        if self.type == "dividend" and (self.amount is None or self.amount < 0):
            raise ValueError("accepting a dividend requires amount >= 0")
        if self.type == "split" and (self.ratio is None or self.ratio <= 0):
            raise ValueError("accepting a split requires ratio > 0")
        return self


class SuggestionDismiss(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    type: Literal["dividend", "split"]
    ex_date: date

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.strip().upper()
