"""Route-level tests for admin account-request management."""

import pytest
from sqlalchemy import select

from app.auth import require_admin, hash_password
from app.models import User, AccountRequest, InviteCode
from tests.test_register_invite_only import make_test_app, client_for


async def make_admin_app():
    app, SessionLocal = await make_test_app()

    admin = User(
        id="admin-id", email="admin@test.com", username="admin",
        hashed_password=hash_password("secret123"), is_admin=True, is_active=True,
    )
    async with SessionLocal() as db:
        db.add(admin)
        await db.commit()

    app.dependency_overrides[require_admin] = lambda: admin
    return app, SessionLocal


async def seed_request(SessionLocal, email="v@test.com", status="pending"):
    async with SessionLocal() as db:
        req = AccountRequest(email=email, status=status)
        db.add(req)
        await db.commit()
        await db.refresh(req)
        return req.id


@pytest.mark.asyncio
async def test_list_requests():
    app, SessionLocal = await make_admin_app()
    try:
        await seed_request(SessionLocal, email="a@test.com")
        await seed_request(SessionLocal, email="b@test.com", status="denied")
        async with client_for(app) as client:
            res = await client.get("/api/admin/account-requests")
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 2
        emails = {r["email"] for r in body["requests"]}
        assert emails == {"a@test.com", "b@test.com"}
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approve_creates_invite_and_returns_link():
    app, SessionLocal = await make_admin_app()
    try:
        req_id = await seed_request(SessionLocal, email="v@test.com")
        async with client_for(app) as client:
            res = await client.post(f"/api/admin/account-requests/{req_id}/approve")
        assert res.status_code == 200
        body = res.json()
        assert "/register?token=" in body["invite_link"]
        assert body["email_sent"] is False  # no SMTP configured in tests

        async with SessionLocal() as db:
            req = await db.get(AccountRequest, req_id)
            assert req.status == "approved"
            assert req.invite_id is not None
            invite = await db.get(InviteCode, req.invite_id)
            assert invite.email == "v@test.com"
            assert invite.token == body["token"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_approve_non_pending_rejected():
    app, SessionLocal = await make_admin_app()
    try:
        req_id = await seed_request(SessionLocal, status="denied")
        async with client_for(app) as client:
            res = await client.post(f"/api/admin/account-requests/{req_id}/approve")
        assert res.status_code == 400
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_deny_marks_denied_and_creates_no_invite():
    app, SessionLocal = await make_admin_app()
    try:
        req_id = await seed_request(SessionLocal)
        async with client_for(app) as client:
            res = await client.post(f"/api/admin/account-requests/{req_id}/deny")
        assert res.status_code == 200

        async with SessionLocal() as db:
            req = await db.get(AccountRequest, req_id)
            assert req.status == "denied"
            assert req.invite_id is None
            invites = (await db.execute(select(InviteCode))).scalars().all()
            assert invites == []
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_non_admin_blocked():
    app, SessionLocal = await make_test_app()  # no require_admin override
    try:
        async with client_for(app) as client:
            res = await client.get("/api/admin/account-requests")
        assert res.status_code in (401, 403)
    finally:
        app.dependency_overrides.clear()
