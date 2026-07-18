import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models.user import User


async def _create_all(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture
def make_client(tmp_path):
    """Returns a factory: make_client(user_id) -> TestClient sharing one DB file."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path}/test.db")
    asyncio.run(_create_all(engine))
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def override_db():
        async with maker() as session:
            yield session
            await session.commit()

    def _make(user_id="u1"):
        user = User(id=user_id, email=f"{user_id}@test.com",
                    username=user_id, hashed_password="x")
        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = lambda: user
        return TestClient(app)

    yield _make
    app.dependency_overrides.clear()


BUY = {"type": "buy", "trade_date": "2026-01-05", "symbol": "AAPL",
       "qty": "10", "price": "100", "fee": "1"}


def test_create_and_list_transaction(make_client):
    client = make_client()
    r = client.post("/api/portfolio/transactions", json=BUY)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["transaction"]["symbol"] == "AAPL"
    assert body["transaction"]["currency"] == "USD"     # derived
    assert isinstance(body["warnings"], list)           # negative cash — no deposit

    r = client.get("/api/portfolio/transactions")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_list_filters_by_symbol_and_type(make_client):
    client = make_client()
    client.post("/api/portfolio/transactions", json=BUY)
    client.post("/api/portfolio/transactions",
                json={"type": "deposit", "trade_date": "2026-01-01",
                      "amount": "1000", "currency": "USD"})
    assert len(client.get("/api/portfolio/transactions?symbol=AAPL").json()) == 1
    assert len(client.get("/api/portfolio/transactions?type=deposit").json()) == 1


def test_malformed_entry_is_422(make_client):
    client = make_client()
    r = client.post("/api/portfolio/transactions",
                    json={"type": "deposit", "trade_date": "2026-01-01",
                          "amount": "1000", "currency": "USD", "symbol": "AAPL"})
    assert r.status_code == 422


def test_edit_and_delete(make_client):
    client = make_client()
    txn_id = client.post("/api/portfolio/transactions", json=BUY).json()["transaction"]["id"]
    r = client.put(f"/api/portfolio/transactions/{txn_id}",
                   json={**BUY, "qty": "20"})
    assert r.status_code == 200
    assert r.json()["transaction"]["qty"] == "20"
    r = client.delete(f"/api/portfolio/transactions/{txn_id}")
    assert r.status_code == 200
    assert client.get("/api/portfolio/transactions").json() == []


def test_user_isolation_404_and_empty_list(make_client):
    client_a = make_client("userA")
    txn_id = client_a.post("/api/portfolio/transactions", json=BUY).json()["transaction"]["id"]
    client_b = make_client("userB")
    assert client_b.get("/api/portfolio/transactions").json() == []
    assert client_b.put(f"/api/portfolio/transactions/{txn_id}", json=BUY).status_code == 404
    assert client_b.delete(f"/api/portfolio/transactions/{txn_id}").status_code == 404


def test_summary_endpoint(make_client):
    client = make_client()
    client.post("/api/portfolio/transactions",
                json={"type": "deposit", "trade_date": "2026-01-01",
                      "amount": "10000", "currency": "USD"})
    client.post("/api/portfolio/transactions", json=BUY)
    with patch("app.services.portfolio_ledger.get_latest_price",
               AsyncMock(return_value=150.0)):
        r = client.get("/api/portfolio/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["currencies"]["USD"]["cash"] == "8999"   # 10000 - 1000 - 1 fee
    assert body["holdings"][0]["market_value"] == "1500.0"  # Pydantic v2 Decimal serialization quirk; cash is "8999"
    assert body["warnings"] == []