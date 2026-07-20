"""Route-level tests: registration is invite-only."""

import pytest
from datetime import datetime, timezone, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.models import User, InviteCode
from app.auth import hash_password


async def make_test_app():
    """Return (app, session_factory) with get_db overridden to in-memory SQLite."""
    from app.main import app

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return app, SessionLocal


def client_for(app):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    )


async def seed_admin_and_invite(SessionLocal, token="tok-valid", **invite_kwargs):
    async with SessionLocal() as db:
        admin = User(
            id="admin-id",
            email="admin@test.com",
            username="admin",
            hashed_password=hash_password("secret123"),
            is_admin=True,
        )
        db.add(admin)
        await db.flush()
        defaults = dict(
            code="CODE0001",
            token=token,
            created_by=admin.id,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
            is_active=True,
        )
        defaults.update(invite_kwargs)
        invite = InviteCode(**defaults)
        db.add(invite)
        await db.commit()


REGISTER_BODY = {
    "email": "new@test.com",
    "username": "newuser",
    "password": "password123",
}


@pytest.mark.asyncio
async def test_register_without_token_rejected():
    app, SessionLocal = await make_test_app()
    try:
        async with client_for(app) as client:
            res = await client.post("/api/auth/register", json=REGISTER_BODY)
        assert res.status_code == 400
        assert res.json()["detail"] == "Invitation required"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_with_valid_token_succeeds():
    app, SessionLocal = await make_test_app()
    try:
        await seed_admin_and_invite(SessionLocal, token="tok-valid")
        async with client_for(app) as client:
            res = await client.post(
                "/api/auth/register",
                json={**REGISTER_BODY, "invite_token": "tok-valid"},
            )
        assert res.status_code == 201
        assert res.json()["email"] == "new@test.com"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_with_expired_token_rejected():
    app, SessionLocal = await make_test_app()
    try:
        await seed_admin_and_invite(
            SessionLocal,
            token="tok-expired",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        async with client_for(app) as client:
            res = await client.post(
                "/api/auth/register",
                json={**REGISTER_BODY, "invite_token": "tok-expired"},
            )
        assert res.status_code == 400
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_bootstrap_still_works_without_token():
    app, SessionLocal = await make_test_app()
    try:
        async with client_for(app) as client:
            res = await client.post("/api/auth/bootstrap", json=REGISTER_BODY)
        assert res.status_code == 201
        assert res.json()["is_admin"] is True
    finally:
        app.dependency_overrides.clear()