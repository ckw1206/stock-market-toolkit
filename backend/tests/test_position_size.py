"""Tests for the ATR-based position-size calculator."""
from datetime import datetime
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from app.models import User
from app.providers.chain import FallbackChain, TaggedValue
from app.services.position_size import (
    InvalidPositionSizeInputError,
    compute_position_size,
    get_position_size,
)


def _trending_df(n=60):
    return pd.DataFrame(
        {
            "Open": [100.0 + i * 0.3 for i in range(n)],
            "High": [101.0 + i * 0.3 for i in range(n)],
            "Low": [99.0 + i * 0.3 for i in range(n)],
            "Close": [100.5 + i * 0.3 for i in range(n)],
            "Volume": [1_000_000 for _ in range(n)],
        },
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
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


class TestComputePositionSize:
    def test_shares_scale_with_account_and_risk(self):
        df = _trending_df()
        small = compute_position_size(df, account=10_000, risk_pct=1, atr_mult=2.0)
        large = compute_position_size(df, account=100_000, risk_pct=1, atr_mult=2.0)
        assert small["shares"] > 0
        assert large["shares"] > small["shares"]

    def test_stop_below_entry_and_take_profits_above(self):
        df = _trending_df()
        plan = compute_position_size(df, account=10_000, risk_pct=1, atr_mult=2.0)
        assert plan["stop"] < plan["entry"]
        assert plan["take_profit_2r"] > plan["entry"]
        assert plan["take_profit_3r"] > plan["take_profit_2r"]

    def test_wider_atr_mult_increases_risk_per_share_and_lowers_shares(self):
        df = _trending_df()
        tight = compute_position_size(df, account=10_000, risk_pct=1, atr_mult=1.0)
        wide = compute_position_size(df, account=10_000, risk_pct=1, atr_mult=4.0)
        assert wide["shares"] <= tight["shares"]

    def test_invalid_account_raises(self):
        df = _trending_df()
        with pytest.raises(InvalidPositionSizeInputError):
            compute_position_size(df, account=0, risk_pct=1)

    def test_invalid_risk_pct_raises(self):
        df = _trending_df()
        with pytest.raises(InvalidPositionSizeInputError):
            compute_position_size(df, account=10_000, risk_pct=0)
        with pytest.raises(InvalidPositionSizeInputError):
            compute_position_size(df, account=10_000, risk_pct=101)

    def test_invalid_atr_mult_raises(self):
        df = _trending_df()
        with pytest.raises(InvalidPositionSizeInputError):
            compute_position_size(df, account=10_000, risk_pct=1, atr_mult=0)


class TestGetPositionSize:
    @pytest.mark.asyncio
    async def test_returns_symbol_and_plan(self):
        df = _trending_df()

        async def mock_get_history(symbol, period, interval):
            return TaggedValue(df, "yfinance", datetime.utcnow())

        with patch("app.services.position_size.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(side_effect=mock_get_history)
            result = await get_position_size("aapl", account=10_000, risk_pct=1, provider=mock_provider)

        assert result["symbol"] == "AAPL"
        assert result["shares"] >= 0
        assert "stop" in result


class TestPositionSizeRoute:
    def test_route_success(self, client):
        df = _trending_df()

        with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            response = client.get(
                "/api/analysis/AAPL/position-size?account=10000&risk_pct=1&atr_mult=2"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["account"] == 10000
        assert "shares" in data

    def test_route_thin_history_returns_422(self, client):
        n = 5
        df = _trending_df(n)

        with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            response = client.get(
                "/api/analysis/THIN/position-size?account=10000&risk_pct=1"
            )

        assert response.status_code == 422

    def test_route_invalid_risk_pct_returns_422_from_query_validation(self, client):
        response = client.get("/api/analysis/AAPL/position-size?account=10000&risk_pct=0")
        assert response.status_code == 422

    def test_route_provider_failure_returns_502(self, client):
        with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(side_effect=RuntimeError("down"))
            response = client.get(
                "/api/analysis/FAILSIZE/position-size?account=10000&risk_pct=1"
            )
        assert response.status_code == 502
