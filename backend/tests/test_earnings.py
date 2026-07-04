"""Tests for earnings-date awareness."""
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from app.models import User
from app.providers.chain import FallbackChain, TaggedValue
from app.services.cache import _store
from app.services.earnings import (
    _fetch_next_earnings_date,
    days_until,
    get_next_earnings_date,
)
from app.services.signals import build_signal_result


@pytest.fixture(autouse=True)
def clear_cache_store():
    _store.clear()
    yield
    _store.clear()


class TestFetchNextEarningsDate:
    def _mock_ticker(self, calendar):
        ticker = MagicMock()
        ticker.calendar = calendar
        return ticker

    def test_returns_next_future_date_from_list(self):
        future = date.today() + timedelta(days=3)
        past = date.today() - timedelta(days=10)
        with patch("app.services.earnings.yf.Ticker", return_value=self._mock_ticker({"Earnings Date": [past, future]})):
            assert _fetch_next_earnings_date("AAPL") == future.isoformat()

    def test_picks_earliest_of_multiple_future_dates(self):
        near = date.today() + timedelta(days=2)
        far = date.today() + timedelta(days=40)
        with patch("app.services.earnings.yf.Ticker", return_value=self._mock_ticker({"Earnings Date": [far, near]})):
            assert _fetch_next_earnings_date("AAPL") == near.isoformat()

    def test_handles_scalar_datetime_value(self):
        future = datetime.combine(date.today() + timedelta(days=5), datetime.min.time())
        with patch("app.services.earnings.yf.Ticker", return_value=self._mock_ticker({"Earnings Date": future})):
            assert _fetch_next_earnings_date("AAPL") == future.date().isoformat()

    def test_returns_none_when_only_past_dates(self):
        past = date.today() - timedelta(days=5)
        with patch("app.services.earnings.yf.Ticker", return_value=self._mock_ticker({"Earnings Date": [past]})):
            assert _fetch_next_earnings_date("AAPL") is None

    def test_returns_none_when_calendar_missing_key(self):
        with patch("app.services.earnings.yf.Ticker", return_value=self._mock_ticker({})):
            assert _fetch_next_earnings_date("AAPL") is None

    def test_returns_none_when_calendar_is_none(self):
        with patch("app.services.earnings.yf.Ticker", return_value=self._mock_ticker(None)):
            assert _fetch_next_earnings_date("AAPL") is None


class TestGetNextEarningsDate:
    @pytest.mark.asyncio
    async def test_returns_value_from_fetch(self):
        future = date.today() + timedelta(days=1)
        with patch("app.services.earnings._fetch_next_earnings_date", return_value=future.isoformat()):
            result = await get_next_earnings_date("EARN1")
        assert result == future.isoformat()

    @pytest.mark.asyncio
    async def test_returns_none_on_provider_exception(self):
        with patch("app.services.earnings._fetch_next_earnings_date", side_effect=RuntimeError("yfinance down")):
            result = await get_next_earnings_date("EARN2")
        assert result is None


class TestDaysUntil:
    def test_none_input_returns_none(self):
        assert days_until(None) is None

    def test_computes_positive_day_count(self):
        target = (date.today() + timedelta(days=7)).isoformat()
        assert days_until(target) == 7

    def test_invalid_string_returns_none(self):
        assert days_until("not-a-date") is None


class TestBuildSignalResultEarningsPenalty:
    def _base_kwargs(self, score=0.8):
        return dict(
            symbol="AAPL", period="3mo", latest_close=100.0, timestamp=None,
            indicators={}, score=score, reasons=[], volume_spike=False,
            breakout=False, high_52w=None, low_52w=None,
        )

    def test_earnings_within_5_days_lowers_confidence_and_warns(self):
        base_confidence = round(min(abs(0.8), 1.0), 2)
        result = build_signal_result(**self._base_kwargs(), days_to_earnings=2)
        assert result["confidence"] < base_confidence
        assert any("Earnings in 2 day" in r for r in result["reasons"])
        assert result["indicators"]["days_to_earnings"] == 2

    def test_earnings_beyond_5_days_no_penalty(self):
        base_confidence = round(min(abs(0.8), 1.0), 2)
        result = build_signal_result(**self._base_kwargs(), days_to_earnings=10)
        assert result["confidence"] == base_confidence
        assert not any("Earnings in" in r for r in result["reasons"])

    def test_no_earnings_date_known_no_penalty(self):
        base_confidence = round(min(abs(0.8), 1.0), 2)
        result = build_signal_result(**self._base_kwargs(), days_to_earnings=None)
        assert result["confidence"] == base_confidence
        assert result["indicators"]["days_to_earnings"] is None

    def test_earnings_today_counts_as_within_window(self):
        result = build_signal_result(**self._base_kwargs(), days_to_earnings=0)
        assert any("Earnings in 0 day" in r for r in result["reasons"])


@pytest.fixture
def mock_user():
    return User(id="1", email="test@test.com", username="testuser", hashed_password="xxx")


@pytest.fixture
def client(mock_user):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.auth import get_current_user

    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield TestClient(app)
    app.dependency_overrides.clear()


class TestAnalysisRouteEarningsWiring:
    def test_route_includes_days_to_earnings_field(self, client):
        n = 60
        rng = np.random.default_rng(7)
        closes = 100 + np.cumsum(rng.normal(0, 0.2, n))
        df = pd.DataFrame(
            {
                "Open": closes - 0.1,
                "High": closes + 0.3,
                "Low": closes - 0.3,
                "Close": closes,
                "Volume": [1_000_000] * n,
            },
            index=pd.date_range("2024-01-01", periods=n, freq="D"),
        )

        with (
            patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider,
            patch("app.services.signals.get_next_earnings_date", AsyncMock(return_value=(date.today() + timedelta(days=3)).isoformat())),
        ):
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            response = client.get("/api/analysis/AAPL?period=3mo")

        assert response.status_code == 200
        data = response.json()
        assert data["indicators"]["days_to_earnings"] == 3
        assert any("Earnings in 3 day" in r for r in data["reasons"])
