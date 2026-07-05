"""Tests for alert snooze and quiet-hours hold/catch-up behavior."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.models import Alert, NotificationSettings, TriggeredAlert, NotificationDelivery
from app.providers.chain import FallbackChain, TaggedValue
from app.services.alert_checker import check_alerts


def _price_df(price: float, n: int = 30) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Open": [price] * n,
            "High": [price + 1] * n,
            "Low": [price - 1] * n,
            "Close": [price] * n,
            "Volume": [1_000_000] * n,
        },
        index=pd.date_range("2026-06-01", periods=n, freq="D"),
    )


@pytest_asyncio.fixture
async def sessionmaker_with_alert():
    """Returns (maker, seed_fn) — seed_fn lets each test configure the one alert/settings row."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    yield maker
    await engine.dispose()


async def _seed(maker, *, snoozed_until=None, quiet_start=None, quiet_end=None):
    async with maker() as db:
        alert = Alert(
            user_id="u1",
            symbol="AAPL",
            condition_type="above",
            threshold=100.0,
            period="1h",
            enabled=True,
            snoozed_until=snoozed_until,
        )
        settings = NotificationSettings(
            user_id="u1",
            discord_webhook_url="https://discord.example/webhook",
            discord_enabled=True,
            email_enabled=False,
            quiet_start=quiet_start,
            quiet_end=quiet_end,
            timezone="UTC",
        )
        db.add(alert)
        db.add(settings)
        await db.commit()
        return alert.id


@pytest.fixture(autouse=True)
def mock_market_open():
    with patch("app.services.market_hours.is_market_open", return_value=True):
        yield


class TestAlertSnooze:
    @pytest.mark.asyncio
    async def test_snoozed_alert_does_not_trigger(self, sessionmaker_with_alert):
        maker = sessionmaker_with_alert
        await _seed(maker, snoozed_until=datetime.now(timezone.utc) + timedelta(hours=1))

        with (
            patch("app.services.alert_checker.AsyncSessionLocal", maker),
            patch("app.services.alert_checker.market_provider", spec=FallbackChain) as mp,
        ):
            mp.get_history = AsyncMock(return_value=TaggedValue(_price_df(150.0), "yfinance", datetime.utcnow()))
            await check_alerts()

        async with maker() as db:
            from sqlalchemy import select

            result = await db.execute(select(TriggeredAlert))
            assert result.scalars().all() == []

    @pytest.mark.asyncio
    async def test_expired_snooze_allows_trigger(self, sessionmaker_with_alert):
        maker = sessionmaker_with_alert
        await _seed(maker, snoozed_until=datetime.now(timezone.utc) - timedelta(minutes=1))

        with (
            patch("app.services.alert_checker.AsyncSessionLocal", maker),
            patch("app.services.alert_checker.market_provider", spec=FallbackChain) as mp,
            patch("app.services.alert_checker._send_discord_notification", AsyncMock(return_value=(True, 204, None))),
        ):
            mp.get_history = AsyncMock(return_value=TaggedValue(_price_df(150.0), "yfinance", datetime.utcnow()))
            await check_alerts()

        async with maker() as db:
            from sqlalchemy import select

            result = await db.execute(select(TriggeredAlert))
            assert len(result.scalars().all()) == 1


def _frozen_datetime(*fixed_values: datetime):
    """A drop-in replacement for the `datetime` class that only fixes `.now()`;
    used to control what check_alerts() sees as "now" across successive calls,
    since quiet-hours logic is otherwise sensitive to real wall-clock time.
    """
    mock_dt = MagicMock(wraps=datetime)
    mock_dt.now.side_effect = list(fixed_values)
    return mock_dt


class TestQuietHours:
    @pytest.mark.asyncio
    async def test_triggers_during_quiet_hours_are_held_not_dispatched(self, sessionmaker_with_alert):
        maker = sessionmaker_with_alert
        # Realistic overnight window; "now" is frozen at 2am UTC, inside it.
        await _seed(maker, quiet_start="23:00", quiet_end="07:00")
        quiet_now = datetime(2026, 7, 4, 2, 0, tzinfo=timezone.utc)

        with (
            patch("app.services.alert_checker.AsyncSessionLocal", maker),
            patch("app.services.alert_checker.market_provider", spec=FallbackChain) as mp,
            patch("app.services.alert_checker.datetime", _frozen_datetime(quiet_now)),
            patch("app.services.alert_checker._send_discord_notification", AsyncMock(return_value=(True, 204, None))) as mock_discord,
        ):
            mp.get_history = AsyncMock(return_value=TaggedValue(_price_df(150.0), "yfinance", datetime.utcnow()))
            await check_alerts()

        mock_discord.assert_not_called()

        async with maker() as db:
            from sqlalchemy import select

            triggered = (await db.execute(select(TriggeredAlert))).scalars().all()
            assert len(triggered) == 1
            assert triggered[0].notified is False
            deliveries = (await db.execute(select(NotificationDelivery))).scalars().all()
            # New behavior: quiet_hold delivery record is written so held alerts are visible
            assert len(deliveries) == 1
            assert deliveries[0].status == "quiet_hold"
            assert deliveries[0].channel == "discord"

    @pytest.mark.asyncio
    async def test_catchup_delivers_once_quiet_hours_end(self, sessionmaker_with_alert):
        maker = sessionmaker_with_alert
        # Same stable overnight window across both runs — this is a fixed
        # daily schedule in practice, not something that changes run-to-run.
        await _seed(maker, quiet_start="23:00", quiet_end="07:00")
        quiet_now = datetime(2026, 7, 4, 2, 0, tzinfo=timezone.utc)   # inside the window
        awake_now = datetime(2026, 7, 4, 10, 0, tzinfo=timezone.utc)  # outside the window

        with (
            patch("app.services.alert_checker.AsyncSessionLocal", maker),
            patch("app.services.alert_checker.market_provider", spec=FallbackChain) as mp,
            patch("app.services.alert_checker.datetime", _frozen_datetime(quiet_now)),
            patch("app.services.alert_checker._send_discord_notification", AsyncMock(return_value=(True, 204, None))) as mock_discord,
        ):
            mp.get_history = AsyncMock(return_value=TaggedValue(_price_df(150.0), "yfinance", datetime.utcnow()))
            await check_alerts()

        mock_discord.assert_not_called()

        with (
            patch("app.services.alert_checker.AsyncSessionLocal", maker),
            patch("app.services.alert_checker.market_provider", spec=FallbackChain) as mp,
            patch("app.services.alert_checker.datetime", _frozen_datetime(awake_now)),
            patch("app.services.alert_checker._send_digest", AsyncMock(return_value=(
                [
                    NotificationDelivery(
                        triggered_alert_id=None,
                        user_id="u1",
                        channel="quiet_digest",
                        status="success",
                        error=None,
                    )
                ],
                True,  # notified
            ))) as mock_digest,
        ):
            # Price now back below threshold so the condition no longer
            # evaluates true — this run must not create a *fresh* trigger;
            # the only call expected is the catch-up digest via _send_digest.
            mp.get_history = AsyncMock(return_value=TaggedValue(_price_df(50.0), "yfinance", datetime.utcnow()))
            await check_alerts()
            mock_digest.assert_called_once()

        async with maker() as db:
            from sqlalchemy import select

            triggered = (await db.execute(select(TriggeredAlert))).scalars().all()
            assert len(triggered) == 1
            assert triggered[0].notified is True
            deliveries = (await db.execute(select(NotificationDelivery))).scalars().all()
            # One quiet_hold from the initial hold, one success from digest catch-up
            assert len(deliveries) == 2
            digest_delivery = next(d for d in deliveries if d.channel == "quiet_digest")
            assert digest_delivery.status == "success"
