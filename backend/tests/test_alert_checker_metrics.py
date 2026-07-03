"""Tests for alert checker signal & rvol metric evaluation."""
import pytest
from unittest.mock import AsyncMock, patch
import pandas as pd


class TestAlertCheckerSignalRvolMetrics:
    """Tests for signal and rvol metric computation in alert checker."""

    @pytest.fixture
    def mock_ohlcv_df(self):
        """A 60-row OHLCV DataFrame with moderate volume."""
        n = 60
        return pd.DataFrame({
            "Open":   [150.0 + i * 0.1 for i in range(n)],
            "High":   [152.0 + i * 0.1 for i in range(n)],
            "Low":    [149.0 + i * 0.1 for i in range(n)],
            "Close":  [151.0 + i * 0.1 for i in range(n)],
            "Volume": [1_000_000 + i * 10_000 for i in range(n)],
        }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

    @pytest.mark.asyncio
    async def test_get_indicators_includes_signal_and_rvol(self, mock_ohlcv_df):
        """_get_indicators returns signal (numeric) and rvol in the result dict."""
        from app.services.alert_checker import _get_indicators

        # Patch _get_ohlcv_df to return our mock df
        with patch("app.services.alert_checker._get_ohlcv_df", new_callable=AsyncMock) as mock_get_df:
            mock_get_df.return_value = mock_ohlcv_df

            indicators = await _get_indicators("AAPL", "1h")

            # signal should be present and be 1, 0, or -1
            assert "signal" in indicators
            assert indicators["signal"] in [-1, 0, 1]
            # rvol should be present and be a float
            assert "rvol" in indicators
            assert isinstance(indicators["rvol"], float)

    @pytest.mark.asyncio
    async def test_signal_evaluate_condition_buysignal(self):
        """AlertCondition with metric=signal operator=eq value=1 triggers for BUY."""
        from app.services.alert_checker import _evaluate_condition
        from app.models import AlertCondition

        condition = AlertCondition(
            id=1,
            alert_id=1,
            metric="signal",
            operator="eq",
            value=1.0,
        )
        indicators = {"signal": 1, "rvol": 1.5}

        result = _evaluate_condition(condition, indicators)
        assert result is True

    @pytest.mark.asyncio
    async def test_signal_evaluate_condition_sellsignal(self):
        """AlertCondition with metric=signal operator=eq value=-1 triggers for SELL."""
        from app.services.alert_checker import _evaluate_condition
        from app.models import AlertCondition

        condition = AlertCondition(
            id=1,
            alert_id=1,
            metric="signal",
            operator="eq",
            value=-1.0,
        )
        indicators = {"signal": -1, "rvol": 1.5}

        result = _evaluate_condition(condition, indicators)
        assert result is True

    @pytest.mark.asyncio
    async def test_rvol_evaluate_condition_above_threshold(self):
        """AlertCondition with metric=rvol operator=gt value=2 triggers when rvol > 2."""
        from app.services.alert_checker import _evaluate_condition
        from app.models import AlertCondition

        condition = AlertCondition(
            id=1,
            alert_id=1,
            metric="rvol",
            operator="gt",
            value=2.0,
        )
        indicators = {"signal": 0, "rvol": 2.5}

        result = _evaluate_condition(condition, indicators)
        assert result is True

    @pytest.mark.asyncio
    async def test_rvol_evaluate_condition_below_threshold(self):
        """AlertCondition with metric=rvol operator=lt value=2 does NOT trigger when rvol = 2.5."""
        from app.services.alert_checker import _evaluate_condition
        from app.models import AlertCondition

        condition = AlertCondition(
            id=1,
            alert_id=1,
            metric="rvol",
            operator="lt",
            value=2.0,
        )
        indicators = {"signal": 0, "rvol": 2.5}

        result = _evaluate_condition(condition, indicators)
        assert result is False

    @pytest.mark.asyncio
    async def test_signal_evaluate_condition_no_match(self):
        """AlertCondition with metric=signal operator=eq value=1 does NOT trigger when signal = 0."""
        from app.services.alert_checker import _evaluate_condition
        from app.models import AlertCondition

        condition = AlertCondition(
            id=1,
            alert_id=1,
            metric="signal",
            operator="eq",
            value=1.0,
        )
        indicators = {"signal": 0, "rvol": 1.5}

        result = _evaluate_condition(condition, indicators)
        assert result is False