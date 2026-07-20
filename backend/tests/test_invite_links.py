"""Invite responses expose a full registration link.

Also includes route-level tests for permanent deletion of invite codes."""
import pytest
import httpx
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.database import Base, get_db
from app.models import InviteCode, AccountRequest, User
from app.auth import require_admin, hash_password
from app.schemas import InviteCodeResponse


def test_invite_code_response_has_invite_link_field():
    assert "invite_link" in InviteCodeResponse.model_fields


def test_build_invite_link_uses_frontend_url(monkeypatch):
    from app.config import get_settings
    from app.routes.admin import build_invite_link

    monkeypatch.setattr(get_settings(), "FRONTEND_URL", "https://stock.example.com/")
    assert build_invite_link("abc123") == "https://stock.example.com/register?token=abc123"


def test_build_invite_link_relative_when_unset(monkeypatch):
    from app.config import get_settings
    from app.routes.admin import build_invite_link

    monkeypatch.setattr(get_settings(), "FRONTEND_URL", "")
    assert build_invite_link("abc123") == "/register?token=abc123"


# ---------------------------------------------------------------------------
# Helpers for route-level tests
# ---------------------------------------------------------------------------


async def make_app():
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


async def seed_admin(SessionLocal) -> User:
    async with SessionLocal() as db:
        admin = User(
            id="admin-id",
            email="admin@test.com",
            username="admin",
            hashed_password=hash_password("secret123"),
            is_admin=True,
            is_active=True,
        )
        db.add(admin)
        await db.commit()
    return admin


async def seed_invite(
    SessionLocal,
    is_active=True,
    used_by=None,
    expires_at=None,
):
    async with SessionLocal() as db:
        if expires_at is None:
            expires_at = datetime.now(timezone.utc) + timedelta(days=7)
        invite = InviteCode(
            code="TESTCODE",
            token="tok-" + ("active" if is_active else "dead"),
            created_by="admin-id",
            expires_at=expires_at,
            is_active=is_active,
            used_by=used_by,
        )
        db.add(invite)
        await db.commit()
        await db.refresh(invite)
        return invite


async def seed_account_request(SessionLocal, invite_id: int) -> AccountRequest:
    async with SessionLocal() as db:
        req = AccountRequest(
            email="req@test.com", status="approved", invite_id=invite_id
        )
        db.add(req)
        await db.commit()
        await db.refresh(req)
        return req


# ---------------------------------------------------------------------------
# Permanent-delete tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_permanent_delete_deactivated_unused_returns_204():
    app, SessionLocal = await make_app()
    try:
        admin = await seed_admin(SessionLocal)
        invite = await seed_invite(SessionLocal, is_active=False)
        app.dependency_overrides[require_admin] = lambda: admin

        async with client_for(app) as client:
            res = await client.delete(
                f"/api/admin/invite-codes/{invite.id}/permanent"
            )
        assert res.status_code == 204

        # Row is really gone
        async with SessionLocal() as db:
            row = await db.get(InviteCode, invite.id)
            assert row is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_permanent_delete_expired_unused_returns_204():
    app, SessionLocal = await make_app()
    try:
        admin = await seed_admin(SessionLocal)
        invite = await seed_invite(
            SessionLocal,
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        app.dependency_overrides[require_admin] = lambda: admin

        async with client_for(app) as client:
            res = await client.delete(
                f"/api/admin/invite-codes/{invite.id}/permanent"
            )
        assert res.status_code == 204

        async with SessionLocal() as db:
            row = await db.get(InviteCode, invite.id)
            assert row is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_permanent_delete_active_unexpired_returns_409():
    app, SessionLocal = await make_app()
    try:
        admin = await seed_admin(SessionLocal)
        invite = await seed_invite(SessionLocal, is_active=True)
        app.dependency_overrides[require_admin] = lambda: admin

        async with client_for(app) as client:
            res = await client.delete(
                f"/api/admin/invite-codes/{invite.id}/permanent"
            )
        assert res.status_code == 409
        assert "active" in res.json()["detail"].lower()

        # Row survives
        async with SessionLocal() as db:
            row = await db.get(InviteCode, invite.id)
            assert row is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_permanent_delete_redeemed_returns_409():
    app, SessionLocal = await make_app()
    try:
        admin = await seed_admin(SessionLocal)
        invite = await seed_invite(
            SessionLocal, is_active=True, used_by="some-user"
        )
        app.dependency_overrides[require_admin] = lambda: admin

        async with client_for(app) as client:
            res = await client.delete(
                f"/api/admin/invite-codes/{invite.id}/permanent"
            )
        assert res.status_code == 409
        assert "used" in res.json()["detail"].lower()

        async with SessionLocal() as db:
            row = await db.get(InviteCode, invite.id)
            assert row is not None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_permanent_delete_account_request_invite_id_nulled():
    app, SessionLocal = await make_app()
    try:
        admin = await seed_admin(SessionLocal)
        invite = await seed_invite(SessionLocal, is_active=False)
        req = await seed_account_request(SessionLocal, invite.id)
        app.dependency_overrides[require_admin] = lambda: admin

        async with client_for(app) as client:
            res = await client.delete(
                f"/api/admin/invite-codes/{invite.id}/permanent"
            )
        assert res.status_code == 204

        # Account request still exists, status unchanged, invite_id is NULL
        async with SessionLocal() as db:
            req_row = await db.get(AccountRequest, req.id)
            assert req_row is not None
            assert req_row.status == "approved"
            assert req_row.invite_id is None

            invite_row = await db.get(InviteCode, invite.id)
            assert invite_row is None
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_permanent_delete_unknown_id_returns_404():
    app, SessionLocal = await make_app()
    try:
        admin = await seed_admin(SessionLocal)
        app.dependency_overrides[require_admin] = lambda: admin

        async with client_for(app) as client:
            res = await client.delete("/api/admin/invite-codes/99999/permanent")
        assert res.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_permanent_delete_non_admin_rejected():
    app, SessionLocal = await make_app()
    try:
        # No require_admin override -> real auth runs -> 401/403
        async with client_for(app) as client:
            res = await client.delete("/api/admin/invite-codes/1/permanent")
        assert res.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()
