"""Tests for the pct_change metric window in the alert checker.

pct_change must measure one Period interval (the interval the user picked in
the alert UI), not the span of the whole fetched history window.
"""
import pytest
from unittest.mock import AsyncMock, patch
import pandas as pd


class TestAlertCheckerPctChangeWindow:
    """pct_change is measured over one Period interval."""

    @pytest.fixture
    def declining_with_final_spike_df(self):
        """5 days of 15m bars drifting down ~1.1%, with a final bar up +1.5%.

        Mirrors a real report: a leveraged ETF that popped 1.5% in the last
        15 minutes while the 5-day window was still negative. A "% Change > 1"
        alert on a 15 min period must fire on the +1.5% bar.
        """
        closes = [100.0 - i * 0.02 for i in range(129)]
        closes.append(closes[-1] * 1.015)  # final 15m bar: +1.5%
        n = len(closes)
        return pd.DataFrame({
            "Open":   closes,
            "High":   [c * 1.002 for c in closes],
            "Low":    [c * 0.998 for c in closes],
            "Close":  closes,
            "Volume": [1_000_000] * n,
        }, index=pd.date_range("2024-01-01", periods=n, freq="15min"))

    @pytest.mark.asyncio
    async def test_pct_change_measures_one_interval_not_whole_window(
        self, declining_with_final_spike_df
    ):
        """pct_change reflects the last 15m bar (+1.5%), not the 5-day span (-1.1%)."""
        from app.services.alert_checker import _get_indicators

        with patch(
            "app.services.alert_checker._get_ohlcv_df", new_callable=AsyncMock
        ) as mock_get_df:
            mock_get_df.return_value = declining_with_final_spike_df

            indicators = await _get_indicators("PCTWINDOW1.TW", "15m")

        assert indicators["pct_change"] == pytest.approx(1.5, abs=0.01)

    @pytest.mark.asyncio
    async def test_pct_change_gt_condition_fires_on_interval_move(
        self, declining_with_final_spike_df
    ):
        """A "% Change > 1" condition triggers on the +1.5% interval move."""
        from app.services.alert_checker import _get_indicators, _evaluate_condition
        from app.models import AlertCondition

        with patch(
            "app.services.alert_checker._get_ohlcv_df", new_callable=AsyncMock
        ) as mock_get_df:
            mock_get_df.return_value = declining_with_final_spike_df

            indicators = await _get_indicators("PCTWINDOW2.TW", "15m")

        condition = AlertCondition(
            id=1, alert_id=1, metric="pct_change", operator="gt", value=1.0
        )

        assert _evaluate_condition(condition, indicators) is True
