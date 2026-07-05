"""Tests for RSI divergence detection."""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import numpy as np
import pandas as pd
import pytest

from app.models import User
from app.providers.chain import FallbackChain, TaggedValue
from app.services.signals import detect_divergence, score_signals


def _piecewise(n: int, anchors: list[tuple[int, float]]) -> pd.Series:
    """Linear interpolation through (index, value) anchors, as a length-n Series."""
    xs = [a[0] for a in anchors]
    ys = [a[1] for a in anchors]
    return pd.Series(np.interp(np.arange(n), xs, ys))


class TestDetectDivergence:
    def test_bullish_divergence_lower_low_price_higher_low_rsi(self):
        close = _piecewise(60, [(0, 110), (15, 90), (30, 110), (45, 82), (59, 105)])
        rsi = _piecewise(60, [(0, 50), (15, 25), (30, 60), (45, 35), (59, 50)])
        assert detect_divergence(close, rsi) == "bullish"

    def test_bearish_divergence_higher_high_price_lower_high_rsi(self):
        close = _piecewise(60, [(0, 90), (15, 110), (30, 90), (45, 118), (59, 95)])
        rsi = _piecewise(60, [(0, 50), (15, 75), (30, 40), (45, 60), (59, 50)])
        assert detect_divergence(close, rsi) == "bearish"

    def test_no_divergence_when_price_and_rsi_move_together(self):
        close = _piecewise(60, [(0, 90), (59, 150)])
        rsi = _piecewise(60, [(0, 30), (59, 70)])
        assert detect_divergence(close, rsi) is None

    def test_returns_none_with_insufficient_lookback(self):
        close = _piecewise(30, [(0, 100), (29, 110)])
        rsi = _piecewise(30, [(0, 40), (29, 60)])
        assert detect_divergence(close, rsi, lookback=60) is None

    def test_returns_none_when_rsi_has_nan_in_window(self):
        close = _piecewise(60, [(0, 110), (15, 90), (30, 110), (45, 82), (59, 105)])
        rsi = _piecewise(60, [(0, 50), (15, 25), (30, 60), (45, 35), (59, 50)])
        rsi.iloc[5] = np.nan
        assert detect_divergence(close, rsi) is None


class TestScoreSignalsDivergenceLeg:
    def _base_kwargs(self):
        return dict(
            bias=None, macd_hist=None, kdj_k=None, kdj_d=None,
            vol_ratio=None, rvol=None, breakout=False, high_52w=None,
        )

    def test_bullish_divergence_adds_positive_leg_and_reason(self):
        score, reasons = score_signals(**self._base_kwargs(), divergence="bullish")
        assert score == 1.0
        assert any("Bullish RSI divergence" in r for r in reasons)

    def test_bearish_divergence_adds_negative_leg_and_reason(self):
        score, reasons = score_signals(**self._base_kwargs(), divergence="bearish")
        assert score == -1.0
        assert any("Bearish RSI divergence" in r for r in reasons)

    def test_no_divergence_leaves_score_unchanged(self):
        score, reasons = score_signals(**self._base_kwargs(), divergence=None)
        assert score == 0.0
        assert reasons == []


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


class TestAnalysisRouteDivergenceWiring:
    def test_route_includes_divergence_field(self, client):
        n = 90
        rng = np.random.default_rng(3)
        closes = 100 + np.cumsum(rng.normal(0, 0.3, n))
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

        with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            response = client.get("/api/analysis/AAPL?period=3mo")

        assert response.status_code == 200
        data = response.json()
        assert "divergence" in data["indicators"]
