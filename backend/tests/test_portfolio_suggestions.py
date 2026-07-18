from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models.portfolio import PortfolioSuggestionDismissal, PortfolioTransaction
from app.services.portfolio_suggestions import build_suggestions


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


def _buy(user_id="u1", symbol="AAPL", trade_date=date(2026, 1, 5), qty="10"):
    return PortfolioTransaction(user_id=user_id, type="buy", trade_date=trade_date,
                                symbol=symbol, qty=qty, price="100", fee="0",
                                currency="USD")


def _mock_provider(dividends=None, splits=None, error=False):
    mock = AsyncMock()
    if error:
        mock.get_dividends.side_effect = RuntimeError("All providers failed")
        mock.get_splits.side_effect = RuntimeError("All providers failed")
    else:
        mock.get_dividends.return_value = dividends if dividends is not None \
            else pd.Series(dtype=float)
        mock.get_splits.return_value = splits if splits is not None \
            else pd.Series(dtype=float)
    return patch("app.services.portfolio_suggestions.fundamentals_provider", mock)


DIVS = pd.Series([0.25], index=[pd.Timestamp("2026-06-10")])


@pytest.mark.asyncio
async def test_dividend_suggested_when_shares_held_on_ex_date(db_session):
    db_session.add(_buy())
    await db_session.commit()
    with _mock_provider(dividends=DIVS):
        out = await build_suggestions(db_session, "u1")
    assert out["degraded"] is False
    (sug,) = out["suggestions"]
    assert sug["symbol"] == "AAPL"
    assert sug["type"] == "dividend"
    assert sug["ex_date"] == date(2026, 6, 10)
    assert sug["shares"] == Decimal("10")
    assert sug["gross_amount"] == Decimal("2.5")      # 10 * 0.25


@pytest.mark.asyncio
async def test_no_suggestion_when_no_shares_on_ex_date(db_session):
    db_session.add(_buy(trade_date=date(2026, 6, 20)))  # bought after ex-date
    await db_session.commit()
    with _mock_provider(dividends=DIVS):
        out = await build_suggestions(db_session, "u1")
    assert out["suggestions"] == []


@pytest.mark.asyncio
async def test_matching_ledger_entry_hides_suggestion(db_session):
    db_session.add(_buy())
    db_session.add(PortfolioTransaction(
        user_id="u1", type="dividend", trade_date=date(2026, 6, 10),
        symbol="AAPL", amount="2.5", fee="0", currency="USD"))
    await db_session.commit()
    with _mock_provider(dividends=DIVS):
        out = await build_suggestions(db_session, "u1")
    assert out["suggestions"] == []


@pytest.mark.asyncio
async def test_dismissal_hides_suggestion(db_session):
    db_session.add(_buy())
    db_session.add(PortfolioSuggestionDismissal(
        user_id="u1", symbol="AAPL", type="dividend", ex_date=date(2026, 6, 10)))
    await db_session.commit()
    with _mock_provider(dividends=DIVS):
        out = await build_suggestions(db_session, "u1")
    assert out["suggestions"] == []


@pytest.mark.asyncio
async def test_split_suggested(db_session):
    db_session.add(_buy(symbol="NVDA"))
    await db_session.commit()
    splits = pd.Series([4.0], index=[pd.Timestamp("2026-06-10")])
    with _mock_provider(splits=splits):
        out = await build_suggestions(db_session, "u1")
    (sug,) = out["suggestions"]
    assert sug["type"] == "split"
    assert sug["ratio"] == Decimal("4")


@pytest.mark.asyncio
async def test_provider_failure_degrades_not_raises(db_session):
    db_session.add(_buy())
    await db_session.commit()
    with _mock_provider(error=True):
        out = await build_suggestions(db_session, "u1")
    assert out["degraded"] is True
    assert out["degraded_symbols"] == ["AAPL"]
    assert out["suggestions"] == []