"""Tests for multi-timeframe (weekly) confluence."""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

from app.models import User
from app.providers.chain import FallbackChain, TaggedValue
from app.services.signals import build_signal_result, weekly_bias, weekly_frame


def _daily_df(n, start=100.0, step=0.0, seed=0):
    rng = np.random.default_rng(seed)
    closes = start + np.cumsum(np.full(n, step)) + rng.normal(0, 0.05, n)
    return pd.DataFrame(
        {
            "Open": closes - 0.1,
            "High": closes + 0.2,
            "Low": closes - 0.2,
            "Close": closes,
            "Volume": [1_000_000] * n,
        },
        index=pd.date_range("2023-01-02", periods=n, freq="D"),
    )


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


class TestWeeklyFrame:
    def test_resamples_to_weekly_ohlcv(self):
        df = _daily_df(30)
        wdf = weekly_frame(df)
        assert len(wdf) > 0
        assert len(wdf) < len(df)
        assert set(["Open", "High", "Low", "Close", "Volume"]).issubset(wdf.columns)


class TestWeeklyBias:
    def test_returns_none_with_insufficient_history(self):
        df = _daily_df(20)
        assert weekly_bias(weekly_frame(df)) is None

    def test_bullish_when_trending_up(self):
        df = _daily_df(400, start=100.0, step=0.3)
        assert weekly_bias(weekly_frame(df)) == "bullish"

    def test_bearish_when_trending_down(self):
        df = _daily_df(400, start=300.0, step=-0.3)
        assert weekly_bias(weekly_frame(df)) == "bearish"

    def test_ten_week_fallback_when_under_40_weeks(self):
        # ~15 weeks of daily bars: not enough for the 40w leg, falls back to 10w.
        df = _daily_df(105, start=100.0, step=0.5)
        assert weekly_bias(weekly_frame(df)) == "bullish"


class TestBuildSignalResultConfluence:
    def _base_kwargs(self, score):
        return dict(
            symbol="AAPL",
            period="3mo",
            latest_close=100.0,
            timestamp=None,
            indicators={},
            score=score,
            reasons=[],
            volume_spike=False,
            breakout=False,
            high_52w=None,
            low_52w=None,
        )

    def test_aligned_bullish_boosts_confidence_and_adds_reason(self):
        result = build_signal_result(**self._base_kwargs(0.8), weekly_bias_val="bullish")
        assert result["signal"] == "BUY"
        assert result["confidence"] > round(min(abs(0.8), 1.0), 2)
        assert result["indicators"]["confluence"] == "aligned"
        assert any("Weekly trend confirms" in r for r in result["reasons"])

    def test_conflicting_bearish_weekly_lowers_confidence_and_warns(self):
        result = build_signal_result(**self._base_kwargs(0.8), weekly_bias_val="bearish")
        assert result["signal"] == "BUY"
        assert result["confidence"] < round(min(abs(0.8), 1.0), 2)
        assert result["indicators"]["confluence"] == "conflict"
        assert any("Caution" in r for r in result["reasons"])

    def test_neutral_weekly_bias_does_not_change_confidence(self):
        base_confidence = round(min(abs(0.8), 1.0), 2)
        result = build_signal_result(**self._base_kwargs(0.8), weekly_bias_val="neutral")
        assert result["confidence"] == base_confidence
        assert result["indicators"]["confluence"] == "neutral"
        assert not any("Weekly" in r or "Caution" in r for r in result["reasons"])

    def test_no_weekly_bias_leaves_confluence_none(self):
        result = build_signal_result(**self._base_kwargs(0.8))
        assert result["indicators"]["confluence"] is None
        assert result["indicators"]["weekly_bias"] is None

    def test_neutral_daily_signal_skips_confluence_regardless_of_weekly(self):
        result = build_signal_result(**self._base_kwargs(0.2), weekly_bias_val="bullish")
        assert result["signal"] == "NEUTRAL"
        assert result["indicators"]["confluence"] is None


class TestAnalysisRouteConfluenceWiring:
    def test_route_includes_confluence_field(self, client):
        daily_df = _daily_df(60, start=100.0, step=0.3, seed=1)
        weekly_source_df = _daily_df(400, start=60.0, step=0.3, seed=2)

        def side_effect(symbol, period, interval):
            if period == "1y":
                return TaggedValue(weekly_source_df, "yfinance", datetime.utcnow())
            return TaggedValue(daily_df, "yfinance", datetime.utcnow())

        with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(side_effect=side_effect)
            response = client.get("/api/analysis/AAPL?period=1mo")

        assert response.status_code == 200
        data = response.json()
        assert "confluence" in data["indicators"]
        assert "weekly_bias" in data["indicators"]
