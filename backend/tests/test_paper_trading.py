"""Tests for the paper-trading portfolio service and /api/paper routes."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import get_current_user
from app.database import Base, get_db
from app.models import PaperPortfolio, User
from app.providers.chain import FallbackChain, TaggedValue
from app.routes import paper
from app.services.paper_trading import (
    InsufficientCashError,
    InsufficientSharesError,
    InvalidQuantityError,
    InvalidSideError,
    QuoteUnavailableError,
    execute_trade,
    get_or_create_portfolio,
    get_portfolio_view,
    get_trade_history,
)


def _quote_df(price: float) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [price - 1],
            "High": [price + 1],
            "Low": [price - 1],
            "Close": [price],
            "Volume": [1_000_000],
        },
        index=pd.date_range("2026-07-01", periods=1, freq="D"),
    )


def _mock_quote(price: float):
    async def _get_history(symbol, period, interval):
        return TaggedValue(_quote_df(price), "yfinance", datetime.utcnow())

    return AsyncMock(side_effect=_get_history)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


class TestGetOrCreatePortfolio:
    @pytest.mark.asyncio
    async def test_creates_with_default_cash(self, db_session):
        portfolio = await get_or_create_portfolio(db_session, "u1")
        assert portfolio.user_id == "u1"
        assert portfolio.cash == 100_000.0

    @pytest.mark.asyncio
    async def test_reuses_existing_portfolio(self, db_session):
        first = await get_or_create_portfolio(db_session, "u1")
        first.cash = 50_000.0
        await db_session.commit()
        second = await get_or_create_portfolio(db_session, "u1")
        assert second.id == first.id
        assert second.cash == 50_000.0


class TestGetOrCreatePortfolioRace:
    """Regression test: the Portfolio page fires GET /portfolio and GET /history
    concurrently on first load, so two requests can race to create the same
    user's portfolio row. This reproduced a real 500 (IntegrityError on the
    unique user_id constraint) against a live server during manual verification.

    A shared-connection StaticPool doesn't cleanly model two independent DB
    connections racing (production uses a real connection pool, one
    connection per request) — it was flaky and unrepresentative here. Instead
    this drives the exact recovery branch deterministically: the initial
    check finds nothing, the INSERT/COMMIT raises IntegrityError (as it
    would when a concurrent request's insert won the race), and the recovery
    path must roll back and return the winner's row instead of raising.
    """

    @pytest.mark.asyncio
    async def test_recovers_by_reselecting_the_winners_row(self, db_session):
        winner = PaperPortfolio(user_id="racer")
        db_session.add(winner)
        await db_session.commit()

        with patch.object(
            db_session, "commit", AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("unique")))
        ):
            portfolio = await get_or_create_portfolio(db_session, "racer")

        assert portfolio.id == winner.id
        assert portfolio.user_id == "racer"

    @pytest.mark.asyncio
    async def test_reraises_if_still_missing_after_rollback(self, db_session):
        """If the row is genuinely missing after rollback (not just a race),
        the original failure must propagate rather than being swallowed."""
        with patch.object(
            db_session, "commit", AsyncMock(side_effect=IntegrityError("stmt", {}, Exception("unique")))
        ):
            with pytest.raises(IntegrityError):
                await get_or_create_portfolio(db_session, "nobody")


class TestExecuteTrade:
    @pytest.mark.asyncio
    async def test_buy_deducts_cash_and_records_trade(self, db_session):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(100.0)
            result = await execute_trade(db_session, "u1", "aapl", "buy", 10)

        assert result == {"symbol": "AAPL", "side": "buy", "qty": 10, "price": 100.0, "cash_after": 99000.0}

    @pytest.mark.asyncio
    async def test_buy_rejects_when_insufficient_cash(self, db_session):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(100.0)
            with pytest.raises(InsufficientCashError):
                await execute_trade(db_session, "u1", "AAPL", "buy", 10_000)

    @pytest.mark.asyncio
    async def test_sell_rejects_when_no_shares_held(self, db_session):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(100.0)
            with pytest.raises(InsufficientSharesError):
                await execute_trade(db_session, "u1", "AAPL", "sell", 5)

    @pytest.mark.asyncio
    async def test_sell_after_buy_credits_cash(self, db_session):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(100.0)
            await execute_trade(db_session, "u1", "AAPL", "buy", 10)
            mp.get_history = _mock_quote(120.0)
            result = await execute_trade(db_session, "u1", "AAPL", "sell", 4)

        assert result["cash_after"] == 99000.0 + 4 * 120.0

    @pytest.mark.asyncio
    async def test_invalid_side_raises(self, db_session):
        with pytest.raises(InvalidSideError):
            await execute_trade(db_session, "u1", "AAPL", "hold", 1)

    @pytest.mark.asyncio
    async def test_non_positive_qty_raises(self, db_session):
        with pytest.raises(InvalidQuantityError):
            await execute_trade(db_session, "u1", "AAPL", "buy", 0)

    @pytest.mark.asyncio
    async def test_quote_unavailable_propagates(self, db_session):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = AsyncMock(side_effect=RuntimeError("provider down"))
            with pytest.raises(QuoteUnavailableError):
                await execute_trade(db_session, "u1", "AAPL", "buy", 1)


class TestGetPortfolioView:
    @pytest.mark.asyncio
    async def test_empty_portfolio(self, db_session):
        view = await get_portfolio_view(db_session, "u1")
        assert view == {"cash": 100_000.0, "positions": [], "equity": 100_000.0, "total_unrealized_pnl": 0.0}

    @pytest.mark.asyncio
    async def test_open_position_marked_to_market(self, db_session):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(100.0)
            await execute_trade(db_session, "u1", "AAPL", "buy", 10)

            mp.get_history = _mock_quote(110.0)
            view = await get_portfolio_view(db_session, "u1")

        assert view["cash"] == 99000.0
        pos = view["positions"][0]
        assert pos["symbol"] == "AAPL"
        assert pos["qty"] == 10
        assert pos["avg_cost"] == 100.0
        assert pos["last_price"] == 110.0
        assert pos["unrealized_pnl"] == 100.0
        assert view["total_unrealized_pnl"] == 100.0
        assert view["equity"] == 99000.0 + 10 * 110.0

    @pytest.mark.asyncio
    async def test_fully_closed_position_not_listed(self, db_session):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(100.0)
            await execute_trade(db_session, "u1", "AAPL", "buy", 5)
            mp.get_history = _mock_quote(105.0)
            await execute_trade(db_session, "u1", "AAPL", "sell", 5)

            view = await get_portfolio_view(db_session, "u1")

        assert view["positions"] == []


class TestGetTradeHistory:
    @pytest.mark.asyncio
    async def test_returns_trades_most_recent_first(self, db_session):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(100.0)
            await execute_trade(db_session, "u1", "AAPL", "buy", 1)
            mp.get_history = _mock_quote(200.0)
            await execute_trade(db_session, "u1", "MSFT", "buy", 1)

            history = await get_trade_history(db_session, "u1")

        assert [t["symbol"] for t in history] == ["MSFT", "AAPL"]


@pytest_asyncio.fixture
async def client(db_session):
    app = FastAPI()
    app.include_router(paper.router)
    app.dependency_overrides[get_current_user] = lambda: User(id="u1", email="t@example.com")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class TestPaperRoutes:
    @pytest.mark.asyncio
    async def test_post_trade_success(self, client):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(50.0)
            resp = await client.post("/api/paper/trade", json={"symbol": "AAPL", "side": "buy", "qty": 20})

        assert resp.status_code == 200
        data = resp.json()
        assert data["cash_after"] == 100_000.0 - 20 * 50.0

    @pytest.mark.asyncio
    async def test_post_trade_insufficient_cash_returns_400(self, client):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(50.0)
            resp = await client.post("/api/paper/trade", json={"symbol": "AAPL", "side": "buy", "qty": 100_000})

        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_post_trade_invalid_qty_returns_422_from_schema_validation(self, client):
        resp = await client.post("/api/paper/trade", json={"symbol": "AAPL", "side": "buy", "qty": -1})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_get_portfolio_returns_view(self, client):
        resp = await client.get("/api/paper/portfolio")
        assert resp.status_code == 200
        assert resp.json()["cash"] == 100_000.0

    @pytest.mark.asyncio
    async def test_get_history_returns_trades(self, client):
        with patch("app.services.paper_trading.market_provider", spec=FallbackChain) as mp:
            mp.get_history = _mock_quote(50.0)
            await client.post("/api/paper/trade", json={"symbol": "AAPL", "side": "buy", "qty": 1})

        resp = await client.get("/api/paper/history")
        assert resp.status_code == 200
        assert len(resp.json()["trades"]) == 1
