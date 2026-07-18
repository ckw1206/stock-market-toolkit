import asyncio
from datetime import date
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.portfolio import PortfolioSuggestionDismissal
from app.models.user import User


async def _create_all(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def client(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    asyncio.run(_create_all(engine))
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db():
        async with maker() as session:
            yield session
            await session.commit()

    user = User(id="u1", email="u1@test.com", username="u1", hashed_password="x")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(engine.dispose())


BUY = {"type": "buy", "trade_date": "2026-01-05", "symbol": "AAPL",
       "qty": "10", "price": "100"}
DIVS = pd.Series([0.25], index=[pd.Timestamp("2026-06-10")])


def _provider(dividends=DIVS):
    mock = AsyncMock()
    mock.get_dividends.return_value = dividends
    mock.get_splits.return_value = pd.Series(dtype=float)
    return patch("app.services.portfolio_suggestions.fundamentals_provider", mock)


def test_get_suggestions(client):
    client.post("/api/portfolio/transactions", json=BUY)
    with _provider():
        r = client.get("/api/portfolio/suggestions")
    assert r.status_code == 200
    body = r.json()
    assert body["degraded"] is False
    assert body["suggestions"][0]["symbol"] == "AAPL"


def test_accept_creates_transaction_and_dismissal(client):
    client.post("/api/portfolio/transactions", json=BUY)
    r = client.post("/api/portfolio/suggestions/accept",
                    json={"symbol": "AAPL", "type": "dividend",
                          "ex_date": "2026-06-10", "amount": "1.75"})
    assert r.status_code == 201, r.text
    assert r.json()["transaction"]["type"] == "dividend"
    assert r.json()["transaction"]["amount"] == "1.75"
    with _provider():
        assert client.get("/api/portfolio/suggestions").json()["suggestions"] == []


def test_accept_split(client):
    client.post("/api/portfolio/transactions", json=BUY)
    r = client.post("/api/portfolio/suggestions/accept",
                    json={"symbol": "AAPL", "type": "split",
                          "ex_date": "2026-06-10", "ratio": "4"})
    assert r.status_code == 201
    assert r.json()["transaction"]["type"] == "split"
    assert r.json()["transaction"]["qty"] == "4"


def test_dismiss_is_idempotent(client):
    client.post("/api/portfolio/transactions", json=BUY)
    payload = {"symbol": "AAPL", "type": "dividend", "ex_date": "2026-06-10"}
    assert client.post("/api/portfolio/suggestions/dismiss", json=payload).status_code == 200
    assert client.post("/api/portfolio/suggestions/dismiss", json=payload).status_code == 200
    with _provider():
        assert client.get("/api/portfolio/suggestions").json()["suggestions"] == []


@pytest.mark.asyncio
async def test_dismiss_pre_inserted_row_is_idempotent(tmp_path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test_pre.db")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    user = User(id="u2", email="u2@test.com", username="u2", hashed_password="x")

    async with maker() as session:
        session.add(PortfolioSuggestionDismissal(
            user_id="u2", symbol="AAPL", type="dividend",
            ex_date=date(2026, 6, 10)))
        await session.commit()

    async def override_db():
        async with maker() as s:
            yield s
            await s.commit()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        with TestClient(app) as c:
            c.post("/api/portfolio/transactions", json=BUY)
            r = c.post("/api/portfolio/suggestions/dismiss",
                       json={"symbol": "AAPL", "type": "dividend", "ex_date": "2026-06-10"})
            assert r.status_code == 200
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()