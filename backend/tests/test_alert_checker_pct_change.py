"""Tests for the pct_change metric anchor in the alert checker.

pct_change (漲跌幅) is today's change vs the previous trading day's close —
the % every quote page shows. The anchor comes from the DAILY feed: Yahoo's
intraday history can contain bars for days the daily feed treats as
non-trading days (seen live on 00631L.TW 2026-07-15), so anchoring inside the
intraday frame silently shifts to the wrong session.
"""
import pytest
from unittest.mock import AsyncMock, patch
import pandas as pd


def _intraday_df(day_closes: dict[str, list[float]], freq: str = "15min") -> pd.DataFrame:
    """Build an intraday OHLCV frame from {date: [closes...]}."""
    closes, index = [], []
    for day, vals in day_closes.items():
        stamps = pd.date_range(f"{day} 09:00", periods=len(vals), freq=freq, tz="Asia/Taipei")
        closes.extend(vals)
        index.extend(stamps)
    return pd.DataFrame({
        "Open":   closes,
        "High":   [c * 1.002 for c in closes],
        "Low":    [c * 0.998 for c in closes],
        "Close":  closes,
        "Volume": [1_000_000] * len(closes),
    }, index=pd.DatetimeIndex(index))


def _daily_df(date_closes: dict[str, float]) -> pd.DataFrame:
    closes = list(date_closes.values())
    return pd.DataFrame({
        "Open": closes, "High": closes, "Low": closes, "Close": closes,
        "Volume": [1_000_000] * len(closes),
    }, index=pd.DatetimeIndex(
        [pd.Timestamp(d, tz="Asia/Taipei") for d in date_closes]
    ))


# Mirrors the real 00631L.TW report on 2026-07-16: previous daily close 35.88
# (daily feed has NO 07-15 row), today drifting up to 36.65 = +2.146% on the
# day, no single 15m bar over ~0.6%. The intraday feed nonetheless contains
# bogus 07-15 bars around 37.17.
DAILY = {"2026-07-10": 36.78, "2026-07-13": 36.86, "2026-07-14": 35.88, "2026-07-16": 36.65}
INTRADAY = {
    "2026-07-14": [36.0, 35.95, 35.88],
    "2026-07-15": [37.10, 37.20, 37.17],  # not in the daily feed
    "2026-07-16": [35.98, 36.16, 36.08, 36.46, 36.65],
}


def _mock_ohlcv(intraday: pd.DataFrame, daily: pd.DataFrame):
    async def loader(symbol, period):
        return daily if period == "1d" else intraday
    return loader


class TestAlertCheckerPctChangeAnchor:
    """pct_change anchors to the daily feed's previous session close."""

    @pytest.mark.asyncio
    async def test_pct_change_is_vs_previous_daily_close(self):
        """pct_change is +2.146% (vs daily 35.88), not the last-bar move and
        not vs the intraday feed's bogus 07-15 session."""
        from app.services.alert_checker import _get_indicators

        with patch(
            "app.services.alert_checker._get_ohlcv_df",
            new=AsyncMock(side_effect=_mock_ohlcv(_intraday_df(INTRADAY), _daily_df(DAILY))),
        ):
            indicators = await _get_indicators("PCTANCHOR1.TW", "15m")

        assert indicators["pct_change"] == pytest.approx((36.65 - 35.88) / 35.88 * 100, abs=0.01)

    @pytest.mark.asyncio
    async def test_crosses_above_fires_on_day_change(self):
        """A "% Change crosses above 2" condition triggers on a +2.1% day."""
        from app.services.alert_checker import _get_indicators, _evaluate_condition
        from app.models import AlertCondition

        with patch(
            "app.services.alert_checker._get_ohlcv_df",
            new=AsyncMock(side_effect=_mock_ohlcv(_intraday_df(INTRADAY), _daily_df(DAILY))),
        ):
            indicators = await _get_indicators("PCTANCHOR2.TW", "15m")

        condition = AlertCondition(
            id=1, alert_id=1, metric="pct_change", operator="crosses_above", value=2.0
        )

        assert _evaluate_condition(condition, indicators) is True

    @pytest.mark.asyncio
    async def test_daily_period_uses_previous_daily_close(self):
        """With a 1d alert period, pct_change is last daily close vs the one before."""
        from app.services.alert_checker import _get_indicators

        daily = _daily_df(DAILY)

        with patch(
            "app.services.alert_checker._get_ohlcv_df",
            new=AsyncMock(side_effect=_mock_ohlcv(daily, daily)),
        ):
            indicators = await _get_indicators("PCTANCHOR3.TW", "1d")

        assert indicators["pct_change"] == pytest.approx((36.65 - 35.88) / 35.88 * 100, abs=0.01)

    @pytest.mark.asyncio
    async def test_no_prior_session_gives_none(self):
        """No daily close before today -> pct_change is None, not a crash."""
        from app.services.alert_checker import _get_indicators

        intraday = _intraday_df({"2026-07-16": [36.0, 36.2, 36.4]})
        daily = _daily_df({"2026-07-16": 36.4})

        with patch(
            "app.services.alert_checker._get_ohlcv_df",
            new=AsyncMock(side_effect=_mock_ohlcv(intraday, daily)),
        ):
            indicators = await _get_indicators("PCTANCHOR4.TW", "15m")

        assert indicators["pct_change"] is None
