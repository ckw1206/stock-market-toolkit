# backend/tests/test_portfolio_summary.py
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.portfolio import PortfolioTransaction
from app.services.portfolio_ledger import ZERO, build_summary, shares_on
from tests.test_portfolio_ledger import txn


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


async def _seed(db, user_id="u1"):
    db.add_all([
        PortfolioTransaction(user_id=user_id, type="deposit",
                             trade_date=date(2026, 1, 1), amount="10000",
                             currency="USD", fee="0"),
        PortfolioTransaction(user_id=user_id, type="buy",
                             trade_date=date(2026, 1, 5), symbol="AAPL",
                             qty="10", price="100", fee="0", currency="USD"),
    ])
    await db.commit()


@pytest.mark.asyncio
async def test_summary_with_live_quote(db_session):
    await _seed(db_session)
    with patch("app.services.portfolio_ledger.get_latest_price",
               AsyncMock(return_value=150.0)):
        summary = await build_summary(db_session, "u1")
    holding = summary["holdings"][0]
    assert holding["symbol"] == "AAPL"
    assert holding["market_value"] == Decimal("1500")
    assert holding["unrealized_pnl"] == Decimal("500")
    usd = summary["currencies"]["USD"]
    assert usd["cash"] == Decimal("9000")
    assert usd["market_value"] == Decimal("1500")
    assert usd["market_value_complete"] is True


@pytest.mark.asyncio
async def test_summary_degrades_when_quote_fails(db_session):
    await _seed(db_session)
    with patch("app.services.portfolio_ledger.get_latest_price",
               AsyncMock(side_effect=RuntimeError("All providers failed"))):
        summary = await build_summary(db_session, "u1")
    holding = summary["holdings"][0]
    assert holding["market_value"] is None
    assert holding["qty"] == Decimal("10")            # rest still computed
    assert summary["currencies"]["USD"]["market_value_complete"] is False


@pytest.mark.asyncio
async def test_summary_only_sees_own_user(db_session):
    await _seed(db_session, user_id="someone_else")
    with patch("app.services.portfolio_ledger.get_latest_price",
               AsyncMock(return_value=150.0)):
        summary = await build_summary(db_session, "u1")
    assert summary["holdings"] == []


def test_shares_on_uses_entries_strictly_before_date():
    txns = [
        txn("buy", "2026-01-05", symbol="AAPL", qty="10", price="100"),
        txn("buy", "2026-03-01", symbol="AAPL", qty="5", price="100"),
    ]
    assert shares_on(txns, "AAPL", date(2026, 2, 1)) == Decimal("10")
    assert shares_on(txns, "AAPL", date(2026, 1, 5)) == ZERO   # same-day excluded
    assert shares_on(txns, "MSFT", date(2026, 2, 1)) == ZERO