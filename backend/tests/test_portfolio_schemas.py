# backend/tests/test_portfolio_schemas.py
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.portfolio import TransactionCreate, derive_currency


def make(**kw):
    base = {"type": "buy", "trade_date": date(2026, 7, 1)}
    base.update(kw)
    return TransactionCreate(**base)


def test_derive_currency():
    assert derive_currency("2330.TW") == "TWD"
    assert derive_currency("6488.TWO") == "TWD"
    assert derive_currency("AAPL") == "USD"


def test_buy_requires_symbol_qty_price():
    txn = make(type="buy", symbol="aapl", qty="10", price="100.5")
    assert txn.symbol == "AAPL"          # uppercased
    assert txn.currency == "USD"         # derived
    assert txn.qty == Decimal("10")
    with pytest.raises(ValidationError):
        make(type="buy", symbol="AAPL", qty="10")            # no price
    with pytest.raises(ValidationError):
        make(type="buy", symbol="AAPL", qty="10", price="1", amount="5")  # amount forbidden


def test_dividend_requires_symbol_amount():
    txn = make(type="dividend", symbol="2330.TW", amount="3500")
    assert txn.currency == "TWD"
    with pytest.raises(ValidationError):
        make(type="dividend", symbol="2330.TW", amount="10", qty="1")  # qty forbidden


def test_deposit_requires_amount_and_currency():
    txn = make(type="deposit", amount="1000", currency="USD")
    assert txn.amount == Decimal("1000")
    with pytest.raises(ValidationError):
        make(type="deposit", amount="1000")                  # cash-only needs currency
    with pytest.raises(ValidationError):
        make(type="deposit", amount="1000", currency="USD", symbol="AAPL")


def test_split_requires_symbol_and_ratio():
    txn = make(type="split", symbol="AAPL", qty="4")
    assert txn.qty == Decimal("4")
    with pytest.raises(ValidationError):
        make(type="split", symbol="AAPL", qty="4", price="1")


def test_adjust_position_and_cash_variants():
    pos = make(type="adjust", symbol="AAPL", qty="0", price="0")  # qty 0 allowed
    assert pos.currency == "USD"
    cash = make(type="adjust", amount="5000", currency="TWD")
    assert cash.amount == Decimal("5000")
    with pytest.raises(ValidationError):
        make(type="adjust", symbol="AAPL", qty="10")          # position needs price
    with pytest.raises(ValidationError):
        make(type="adjust", amount="5000")                    # cash needs currency


def test_currency_override_allowed():
    txn = make(type="buy", symbol="AAPL", qty="1", price="1", currency="TWD")
    assert txn.currency == "TWD"
