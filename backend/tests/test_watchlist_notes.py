"""Tests for watchlist notes/tags: PATCH /api/watchlist/{symbol}."""

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import get_current_user
from app.database import Base, get_db
from app.models import User, Watchlist
from app.routes import watchlist


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    app = FastAPI()
    app.include_router(watchlist.router)
    app.dependency_overrides[get_current_user] = lambda: User(id="u1", email="t@example.com")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed_watchlist_item(db_session, symbol="AAPL", user_id="u1") -> int:
    item = Watchlist(user_id=user_id, symbol=symbol)
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)
    return item.id


class TestUpdateWatchlistItem:
    @pytest.mark.asyncio
    async def test_set_note(self, client, db_session):
        await _seed_watchlist_item(db_session)
        resp = await client.patch("/api/watchlist/AAPL", json={"note": "swing trade idea"})
        assert resp.status_code == 200
        assert resp.json()["note"] == "swing trade idea"
        assert resp.json()["tags"] == []

    @pytest.mark.asyncio
    async def test_set_tags_lowercased_and_deduped(self, client, db_session):
        await _seed_watchlist_item(db_session)
        resp = await client.patch(
            "/api/watchlist/AAPL", json={"tags": ["Swing", "Earnings-Play", "swing", "  "]}
        )
        assert resp.status_code == 200
        assert resp.json()["tags"] == ["earnings-play", "swing"]

    @pytest.mark.asyncio
    async def test_note_and_tags_together(self, client, db_session):
        await _seed_watchlist_item(db_session)
        resp = await client.patch(
            "/api/watchlist/AAPL",
            json={"note": "long term", "tags": ["core"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["note"] == "long term"
        assert data["tags"] == ["core"]

    @pytest.mark.asyncio
    async def test_clearing_note_with_empty_string(self, client, db_session):
        await _seed_watchlist_item(db_session)
        await client.patch("/api/watchlist/AAPL", json={"note": "temp"})
        resp = await client.patch("/api/watchlist/AAPL", json={"note": ""})
        assert resp.status_code == 200
        assert resp.json()["note"] is None

    @pytest.mark.asyncio
    async def test_partial_update_preserves_other_field(self, client, db_session):
        await _seed_watchlist_item(db_session)
        await client.patch("/api/watchlist/AAPL", json={"note": "keep me", "tags": ["core"]})
        resp = await client.patch("/api/watchlist/AAPL", json={"tags": ["swing"]})
        assert resp.status_code == 200
        data = resp.json()
        assert data["note"] == "keep me"
        assert data["tags"] == ["swing"]

    @pytest.mark.asyncio
    async def test_symbol_case_insensitive(self, client, db_session):
        await _seed_watchlist_item(db_session, symbol="AAPL")
        resp = await client.patch("/api/watchlist/aapl", json={"note": "x"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_missing_symbol_returns_404(self, client):
        resp = await client.patch("/api/watchlist/MSFT", json={"note": "x"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_scoped_to_owning_user(self, client, db_session):
        await _seed_watchlist_item(db_session, symbol="GOOGL", user_id="someone-else")
        resp = await client.patch("/api/watchlist/GOOGL", json={"note": "x"})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_empty_body_is_a_noop(self, client, db_session):
        await _seed_watchlist_item(db_session)
        await client.patch("/api/watchlist/AAPL", json={"note": "keep", "tags": ["core"]})
        resp = await client.patch("/api/watchlist/AAPL", json={})
        assert resp.status_code == 200
        data = resp.json()
        assert data["note"] == "keep"
        assert data["tags"] == ["core"]


class TestListWatchlistIncludesNotesAndTags:
    @pytest.mark.asyncio
    async def test_list_returns_note_and_tags(self, client, db_session):
        await _seed_watchlist_item(db_session)
        await client.patch("/api/watchlist/AAPL", json={"note": "hi", "tags": ["core"]})

        resp = await client.get("/api/watchlist")
        assert resp.status_code == 200
        data = resp.json()
        assert data[0]["note"] == "hi"
        assert data[0]["tags"] == ["core"]

    @pytest.mark.asyncio
    async def test_list_defaults_tags_to_empty_list(self, client, db_session):
        await _seed_watchlist_item(db_session)
        resp = await client.get("/api/watchlist")
        assert resp.json()[0]["tags"] == []
