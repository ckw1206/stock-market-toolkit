"""Tests for POST /api/alerts/{id}/snooze and quiet-hours settings round-trip.

Uses dependency_overrides for both get_current_user and get_db so these
tests never touch the real configured DATABASE_URL (the project's own
sqlite dev file) — matching the pattern in test_paper_trading.py.
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.auth import get_current_user
from app.database import Base, get_db
from app.models import Alert, User
from app.routes import alerts


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
    app.include_router(alerts.router)
    app.dependency_overrides[get_current_user] = lambda: User(id="u1", email="t@example.com")

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def _seed_alert(db_session) -> int:
    alert = Alert(
        user_id="u1", symbol="AAPL", condition_type="above",
        threshold=100.0, period="1h", enabled=True,
    )
    db_session.add(alert)
    await db_session.commit()
    await db_session.refresh(alert)
    return alert.id


class TestSnoozeRoute:
    @pytest.mark.asyncio
    async def test_snooze_sets_future_snoozed_until(self, client, db_session):
        alert_id = await _seed_alert(db_session)
        resp = await client.post(f"/api/alerts/{alert_id}/snooze", json={"minutes": 60})

        assert resp.status_code == 200
        data = resp.json()
        assert data["snoozed_until"] is not None
        snoozed_at = datetime.fromisoformat(data["snoozed_until"].replace("Z", "+00:00"))
        assert snoozed_at > datetime.now(timezone.utc)

    @pytest.mark.asyncio
    async def test_snooze_zero_clears_existing_snooze(self, client, db_session):
        alert_id = await _seed_alert(db_session)
        await client.post(f"/api/alerts/{alert_id}/snooze", json={"minutes": 60})

        resp = await client.post(f"/api/alerts/{alert_id}/snooze", json={"minutes": 0})
        assert resp.status_code == 200
        assert resp.json()["snoozed_until"] is None

    @pytest.mark.asyncio
    async def test_snooze_response_includes_utc_offset(self, client, db_session):
        """Regression test: the response's snoozed_until must carry an
        explicit UTC offset (e.g. "+00:00" or "Z").

        Found via manual browser verification in a non-UTC environment: the
        route used to re-query the alert from the DB after commit, and
        SQLite silently drops tzinfo on DateTime(timezone=True) columns.
        The resulting offset-less ISO string is ambiguous to JS `Date`
        parsing (treated as local time, not UTC), which made the frontend's
        "snoozed" badge silently disappear for an alert that was still
        actively snoozed.
        """
        alert_id = await _seed_alert(db_session)
        resp = await client.post(f"/api/alerts/{alert_id}/snooze", json={"minutes": 60})

        assert resp.status_code == 200
        snoozed_until_raw = resp.json()["snoozed_until"]
        parsed = datetime.fromisoformat(snoozed_until_raw.replace("Z", "+00:00"))
        assert parsed.tzinfo is not None, (
            f"snoozed_until must include a UTC offset, got {snoozed_until_raw!r}"
        )

    @pytest.mark.asyncio
    async def test_snooze_missing_alert_returns_404(self, client):
        resp = await client.post("/api/alerts/9999/snooze", json={"minutes": 30})
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_snooze_negative_minutes_returns_422(self, client, db_session):
        alert_id = await _seed_alert(db_session)
        resp = await client.post(f"/api/alerts/{alert_id}/snooze", json={"minutes": -5})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_snooze_scoped_to_owning_user(self, client, db_session):
        other = Alert(
            user_id="someone-else", symbol="MSFT", condition_type="above",
            threshold=1.0, period="1h", enabled=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)

        resp = await client.post(f"/api/alerts/{other.id}/snooze", json={"minutes": 30})
        assert resp.status_code == 404


class TestQuietHoursSettings:
    @pytest.mark.asyncio
    async def test_settings_roundtrip_quiet_hours(self, client):
        resp = await client.put(
            "/api/alerts/settings",
            json={
                "email_enabled": False,
                "discord_enabled": True,
                "default_period": "1h",
                "timezone": "America/New_York",
                "quiet_start": "23:00",
                "quiet_end": "07:00",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["quiet_start"] == "23:00"
        assert data["quiet_end"] == "07:00"
        assert data["timezone"] == "America/New_York"

    @pytest.mark.asyncio
    async def test_invalid_quiet_hours_format_returns_422(self, client):
        resp = await client.put(
            "/api/alerts/settings",
            json={
                "email_enabled": False,
                "discord_enabled": True,
                "default_period": "1h",
                "timezone": "UTC",
                "quiet_start": "11pm",
                "quiet_end": "07:00",
            },
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_settings_update_can_clear_quiet_hours(self, client):
        await client.put(
            "/api/alerts/settings",
            json={
                "email_enabled": False, "discord_enabled": True,
                "default_period": "1h", "timezone": "UTC",
                "quiet_start": "23:00", "quiet_end": "07:00",
            },
        )
        resp = await client.put(
            "/api/alerts/settings",
            json={
                "email_enabled": False, "discord_enabled": True,
                "default_period": "1h", "timezone": "UTC",
                "quiet_start": None, "quiet_end": None,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["quiet_start"] is None
        assert resp.json()["quiet_end"] is None
