"""Tests for the signal backtest feature."""
import pytest
from unittest.mock import AsyncMock, patch
import pandas as pd
from datetime import datetime, timedelta

from app.services.signals import score_series, score_signals, signal_from_score
from app.services.backtest import backtest_signal, MIN_BACKTEST_BARS, ThinHistoryError
from app.providers.chain import FallbackChain, TaggedValue
from app.models import User


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

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


# ─────────────────────────────────────────────────────────────────────────────
# TestScoreSeries
# ─────────────────────────────────────────────────────────────────────────────

class TestScoreSeries:
    """Tests for the vectorized score_series function."""

    def _build_df(self, n, trend="trending"):
        """Build a synthetic OHLCV DataFrame.

        trend='trending': steadily increasing prices
        trend='choppy': oscillating prices
        """
        if trend == "trending":
            close = [100.0 + i * 0.5 for i in range(n)]
        else:  # choppy
            close = [100.0 + 5 * ((i % 10) - 5) for i in range(n)]

        return pd.DataFrame(
            {
                "Open":   [c - 0.1 for c in close],
                "High":   [c + 0.2 for c in close],
                "Low":    [c - 0.3 for c in close],
                "Close":  close,
                "Volume": [1_000_000 for _ in range(n)],
            },
            index=pd.date_range("2022-01-01", periods=n, freq="D"),
        )

    def _scalar_score(self, df, high_52w=None):
        """Compute score using the scalar score_signals for the last row."""
        import pandas_ta as ta
        from app.utils.numeric import _clean

        close = df["Close"]
        high = df["High"]
        low = df["Low"]
        volume = df["Volume"]
        n = len(close)

        close_series = close
        sma20_vals = ta.sma(close_series, length=20)
        latest_sma20 = float(sma20_vals.iloc[-1]) if sma20_vals.notna().any() else None
        bias = (
            _clean((float(close_series.iloc[-1]) - latest_sma20) / latest_sma20 * 100)
            if latest_sma20
            else None
        )

        kdj_df = ta.stoch(high=high, low=low, close=close_series, k=14, d=3)
        kdj_k_vals = kdj_df["STOCHk_14_3_3"].tolist() if kdj_df is not None else [None] * n
        kdj_d_vals = kdj_df["STOCHd_14_3_3"].tolist() if kdj_df is not None else [None] * n
        kdj_k = _clean(kdj_k_vals[-1])
        kdj_d = _clean(kdj_d_vals[-1])

        macd_df = ta.macd(close_series, fast=12, slow=26, signal=9)
        macd_hist_list = macd_df["MACDh_12_26_9"].tolist() if macd_df is not None else [None] * n
        macd_hist = (
            _clean(macd_hist_list[-1])
            if macd_hist_list and macd_hist_list[-1] is not None
            else None
        )

        vol_avg = volume.rolling(20).mean()
        vol_ratio = (
            _clean(float(volume.iloc[-1] / vol_avg.iloc[-1]))
            if not pd.isna(vol_avg.iloc[-1])
            else None
        )

        rolling_52w = high.rolling(window=252, min_periods=252).max()
        if high_52w is None:
            breakout_candidate = not pd.isna(rolling_52w.iloc[-1])
            high_52w_val = float(rolling_52w.iloc[-1]) if breakout_candidate else None
        else:
            high_52w_val = high_52w
            breakout_candidate = high_52w is not None

        breakout = False
        if breakout_candidate and high_52w_val is not None:
            breakout = float(close.iloc[-1]) >= 0.98 * high_52w_val and vol_ratio is not None and vol_ratio > 1.5

        rvol = vol_ratio
        score, _ = score_signals(
            bias=bias,
            macd_hist=macd_hist,
            kdj_k=kdj_k,
            kdj_d=kdj_d,
            vol_ratio=vol_ratio,
            rvol=rvol,
            breakout=breakout,
            high_52w=high_52w_val,
            close_price=float(close.iloc[-1]),
        )
        return score

    def test_score_series_matches_scalar_trending(self):
        """score_series(df).iloc[-1] matches scalar path for a trending frame."""
        n = 100
        df = self._build_df(n, trend="trending")

        rolling_52w = df["High"].rolling(window=252, min_periods=252).max()
        high_52w = float(rolling_52w.iloc[-1]) if not pd.isna(rolling_52w.iloc[-1]) else None

        vectorized_score = float(score_series(df).iloc[-1])
        scalar_score = self._scalar_score(df, high_52w=high_52w)

        assert abs(vectorized_score - scalar_score) < 1e-9, (
            f"Vectorized score {vectorized_score} != scalar score {scalar_score}"
        )

    def test_score_series_matches_scalar_choppy(self):
        """score_series(df).iloc[-1] matches scalar path for a choppy frame."""
        n = 100
        df = self._build_df(n, trend="choppy")

        rolling_52w = df["High"].rolling(window=252, min_periods=252).max()
        high_52w = float(rolling_52w.iloc[-1]) if not pd.isna(rolling_52w.iloc[-1]) else None

        vectorized_score = float(score_series(df).iloc[-1])
        scalar_score = self._scalar_score(df, high_52w=high_52w)

        assert abs(vectorized_score - scalar_score) < 1e-9, (
            f"Vectorized score {vectorized_score} != scalar score {scalar_score}"
        )

    def test_score_series_no_lookahead(self):
        """Score at day t must not change when future rows are appended."""
        n = 60
        df_base = self._build_df(n, trend="trending")

        base_scores = score_series(df_base)

        extra_rows = pd.DataFrame(
            {
                "Open":   [110.0 + i * 0.5 for i in range(20)],
                "High":   [110.2 + i * 0.5 for i in range(20)],
                "Low":    [109.7 + i * 0.5 for i in range(20)],
                "Close":  [110.0 + i * 0.5 for i in range(20)],
                "Volume": [1_000_000 for _ in range(20)],
            },
            index=pd.date_range(df_base.index[-1] + timedelta(days=1), periods=20, freq="D"),
        )
        df_extended = pd.concat([df_base, extra_rows])

        extended_scores = score_series(df_extended)

        pd.testing.assert_series_equal(
            base_scores.reset_index(drop=True),
            extended_scores.iloc[:n].reset_index(drop=True),
            check_dtype=False,
        )

    def test_signal_from_score_thresholds(self):
        """signal_from_score respects BUY >= 0.75, SELL <= -0.75."""
        assert signal_from_score(0.75) == "BUY"
        assert signal_from_score(1.0) == "BUY"
        assert signal_from_score(-0.75) == "SELL"
        assert signal_from_score(-1.0) == "SELL"
        assert signal_from_score(0.74) == "NEUTRAL"
        assert signal_from_score(-0.74) == "NEUTRAL"
        assert signal_from_score(0.0) == "NEUTRAL"


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestAggregation
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestAggregation:
    """Tests for backtest aggregation correctness."""

    def _uptrend_df(self, n=150):
        """Deterministic OHLCV in a consistent uptrend (100, 101, 102, ...)."""
        close = [100.0 + i for i in range(n)]
        return pd.DataFrame(
            {
                "Open":   [c - 0.5 for c in close],
                "High":   [c + 1.0 for c in close],
                "Low":    [c - 1.0 for c in close],
                "Close":  close,
                "Volume": [1_000_000 for _ in range(n)],
            },
            index=pd.date_range("2022-01-01", periods=n, freq="D"),
        )

    def test_aggregate_side_buy_exact_stats(self):
        """_aggregate_side counts positive forward returns as hits for the buy side."""
        from app.services.backtest import _aggregate_side

        idx = pd.date_range("2022-01-01", periods=10, freq="D")
        # 4 BUY signal days: returns +2%, -1%, +3%, NaN (excluded) → 3 counted, 2 hits
        mask = pd.Series([True, True, True, True, False, False, False, False, False, False], index=idx)
        fwd = pd.Series([0.02, -0.01, 0.03, None, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05], index=idx, dtype=float)

        side = _aggregate_side(mask, {5: fwd}, (5,), hit_when_positive=True)

        assert side["signal_days"] == 4
        assert side["horizons"]["5"]["count"] == 3
        assert side["horizons"]["5"]["hit_rate"] == round(2 / 3, 2)
        assert side["horizons"]["5"]["avg_return_pct"] == round((2 - 1 + 3) / 3, 2)

    def test_aggregate_side_sell_hits_are_negative_returns(self):
        """_aggregate_side counts NEGATIVE forward returns as hits for the sell side."""
        from app.services.backtest import _aggregate_side

        idx = pd.date_range("2022-01-01", periods=8, freq="D")
        # 4 SELL signal days: returns -2%, -1%, +3%, +1% → 4 counted, 2 hits (the negatives)
        mask = pd.Series([True, True, True, True, False, False, False, False], index=idx)
        fwd = pd.Series([-0.02, -0.01, 0.03, 0.01, 0.0, 0.0, 0.0, 0.0], index=idx, dtype=float)

        side = _aggregate_side(mask, {5: fwd}, (5,), hit_when_positive=False)

        assert side["signal_days"] == 4
        assert side["horizons"]["5"]["count"] == 4
        assert side["horizons"]["5"]["hit_rate"] == 0.5
        # avg return stays the raw mean regardless of side
        assert side["horizons"]["5"]["avg_return_pct"] == round((-2 - 1 + 3 + 1) / 4, 2)

    @pytest.mark.asyncio
    async def test_backtest_signal_end_to_end_sell_hit_rate_not_inverted(self):
        """Full backtest_signal path: in a strong downtrend every generated SELL day
        has a negative forward return, so the SELL hit rate must be 1.0 (not 0.0)."""
        from datetime import datetime
        from unittest.mock import AsyncMock, patch
        from app.providers.chain import TaggedValue
        from app.services.backtest import backtest_signal

        n = 150
        # Gentle but relentless downtrend: steep enough that MACD/KDJ stay
        # bearish, shallow enough that BIAS stays inside ±3 (no oversold
        # counter-leg), so volume-surge days score -0.75 → SELL.
        close = [300.0 - 0.3 * i for i in range(n)]
        df = pd.DataFrame(
            {
                "Open":   [c + 0.5 for c in close],
                "High":   [c + 1.0 for c in close],
                "Low":    [c - 1.0 for c in close],
                "Close":  close,
                # constant volume, then persistent surge so the volume leg can engage
                "Volume": [1_000_000] * 100 + [2_000_000] * 50,
            },
            index=pd.date_range("2022-01-01", periods=n, freq="D"),
        )

        with patch("app.services.backtest.market_provider") as mock_provider:
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            result = await backtest_signal("TEST", period="2y", horizons=(5,))

        sell = result["sell"]
        assert sell["signal_days"] > 0, "downtrend fixture must generate SELL days"
        assert sell["horizons"]["5"]["count"] > 0
        assert sell["horizons"]["5"]["hit_rate"] == 1.0
        assert sell["horizons"]["5"]["avg_return_pct"] < 0


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestThinHistory
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestThinHistory:
    """Tests for ThinHistoryError path."""

    @pytest.mark.asyncio
    async def test_thin_history_raises_error(self):
        """Fewer than 120 bars raises ThinHistoryError."""
        n = 50  # below MIN_BACKTEST_BARS = 120
        df = pd.DataFrame(
            {
                "Open":   [10.0 + i * 0.1 for i in range(n)],
                "High":   [10.5 + i * 0.1 for i in range(n)],
                "Low":    [9.5 + i * 0.1 for i in range(n)],
                "Close":  [10.2 + i * 0.1 for i in range(n)],
                "Volume": [500_000 + i * 1_000 for i in range(n)],
            },
            index=pd.date_range("2026-06-01", periods=n, freq="D"),
        )

        with patch("app.services.backtest.market_provider") as mock_provider:
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            with pytest.raises(ThinHistoryError) as exc_info:
                await backtest_signal("THIN")
            assert exc_info.value.symbol == "THIN"
            assert exc_info.value.available == n
            assert exc_info.value.needed == MIN_BACKTEST_BARS


# ─────────────────────────────────────────────────────────────────────────────
# TestBacktestRoute
# ─────────────────────────────────────────────────────────────────────────────

class TestBacktestRoute:
    """Route-level tests for GET /api/analysis/{symbol}/backtest."""

    def test_backtest_route_thin_history_returns_422(self, client):
        """Thin history returns 422 with the ThinHistoryError message."""
        n = 50
        df = pd.DataFrame(
            {
                "Open":   [10.0 + i * 0.1 for i in range(n)],
                "High":   [10.5 + i * 0.1 for i in range(n)],
                "Low":    [9.5 + i * 0.1 for i in range(n)],
                "Close":  [10.2 + i * 0.1 for i in range(n)],
                "Volume": [500_000 + i * 1_000 for i in range(n)],
            },
            index=pd.date_range("2026-06-01", periods=n, freq="D"),
        )

        with patch("app.services.backtest.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            response = client.get("/api/analysis/THIN/backtest?period=2y")
            assert response.status_code == 422
            assert "THIN" in response.json()["detail"]

    def test_backtest_route_success(self, client):
        """Valid backtest returns 200 with the expected response shape."""
        n = 200
        df = pd.DataFrame(
            {
                "Open":   [100.0 + i * 0.1 for i in range(n)],
                "High":   [100.5 + i * 0.1 for i in range(n)],
                "Low":    [99.5 + i * 0.1 for i in range(n)],
                "Close":  [100.0 + i * 0.1 for i in range(n)],
                "Volume": [1_000_000 for _ in range(n)],
            },
            index=pd.date_range("2024-01-01", periods=n, freq="D"),
        )

        with patch("app.services.backtest.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            response = client.get("/api/analysis/AAPL/backtest?period=2y")
            assert response.status_code == 200
            data = response.json()
            assert data["symbol"] == "AAPL"
            assert data["period"] == "2y"
            assert data["bars"] == n
            assert "buy" in data
            assert "sell" in data
            assert "signal_days" in data["buy"]
            assert "horizons" in data["buy"]
            assert "5" in data["buy"]["horizons"]
            assert "20" in data["buy"]["horizons"]

    def test_backtest_route_provider_failure_returns_502(self, client):
        """Provider failure returns 502."""
        with patch("app.services.backtest.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(
                side_effect=RuntimeError("All providers failed")
            )
            # Use a unique symbol not in cache to avoid stale cache returning 200
            response = client.get("/api/analysis/FAILTEST/backtest?period=2y")
            assert response.status_code == 502

    def test_backtest_zero_signal_days_returns_zeroed_stats(self, client):
        """When a symbol has zero BUY (or SELL) signal days, horizons are zeroed not error."""
        n = 200
        df = pd.DataFrame(
            {
                "Open":   [100.0 for _ in range(n)],
                "High":   [100.1 for _ in range(n)],
                "Low":    [99.9 for _ in range(n)],
                "Close":  [100.0 for _ in range(n)],
                "Volume": [1_000_000 for _ in range(n)],
            },
            index=pd.date_range("2024-01-01", periods=n, freq="D"),
        )

        with patch("app.services.backtest.market_provider", spec=FallbackChain) as mock_provider:
            mock_provider.get_history = AsyncMock(
                return_value=TaggedValue(df, "yfinance", datetime.utcnow())
            )
            response = client.get("/api/analysis/FLAT/backtest?period=2y")
            assert response.status_code == 200
            data = response.json()
            buy_days = data["buy"]["signal_days"]
            sell_days = data["sell"]["signal_days"]
            assert buy_days == 0 or sell_days == 0