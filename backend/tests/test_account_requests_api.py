"""Route-level tests for the public account-request endpoint."""

import pytest
from sqlalchemy import select

from app.models import User, AccountRequest
from app.auth import hash_password
from tests.test_register_invite_only import make_test_app, client_for

GENERIC_MSG = "Request received. An administrator will review it."


@pytest.mark.asyncio
async def test_request_account_creates_pending_row():
    app, SessionLocal = await make_test_app()
    try:
        async with client_for(app) as client:
            res = await client.post(
                "/api/auth/request-account",
                json={"email": "visitor@test.com", "note": "please let me in"},
            )
        assert res.status_code == 200
        assert res.json()["message"] == GENERIC_MSG

        async with SessionLocal() as db:
            rows = (await db.execute(select(AccountRequest))).scalars().all()
        assert len(rows) == 1
        assert rows[0].email == "visitor@test.com"
        assert rows[0].status == "pending"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_duplicate_pending_request_no_second_row_same_response():
    app, SessionLocal = await make_test_app()
    try:
        async with client_for(app) as client:
            await client.post("/api/auth/request-account", json={"email": "v@test.com"})
            res = await client.post("/api/auth/request-account", json={"email": "v@test.com"})
        assert res.status_code == 200
        assert res.json()["message"] == GENERIC_MSG

        async with SessionLocal() as db:
            rows = (await db.execute(select(AccountRequest))).scalars().all()
        assert len(rows) == 1
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_request_account_flood_cap_at_100_pending():
    app, SessionLocal = await make_test_app()
    try:
        async with SessionLocal() as db:
            for i in range(100):
                db.add(AccountRequest(email=f"flood{i}@test.com", status="pending"))
            await db.commit()

        async with client_for(app) as client:
            res = await client.post(
                "/api/auth/request-account",
                json={"email": "newcomer@test.com", "note": "let me in"},
            )
        assert res.status_code == 200
        assert res.json()["message"] == GENERIC_MSG

        async with SessionLocal() as db:
            rows = (await db.execute(select(AccountRequest))).scalars().all()
        assert len(rows) == 100
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_existing_user_email_no_row_same_response():
    app, SessionLocal = await make_test_app()
    try:
        async with SessionLocal() as db:
            db.add(User(
                id="u1", email="taken@test.com", username="taken",
                hashed_password=hash_password("password123"),
            ))
            await db.commit()

        async with client_for(app) as client:
            res = await client.post("/api/auth/request-account", json={"email": "taken@test.com"})
        assert res.status_code == 200
        assert res.json()["message"] == GENERIC_MSG

        async with SessionLocal() as db:
            rows = (await db.execute(select(AccountRequest))).scalars().all()
        assert len(rows) == 0
    finally:
        app.dependency_overrides.clear()
