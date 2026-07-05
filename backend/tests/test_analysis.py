"""Tests for analysis routes (GET /api/analysis/{symbol}, GET /api/analysis/signals)."""
import pytest
import pandas as pd
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_current_user
from app.models import User


@pytest.fixture
def mock_user():
    return User(id="1", email="test@test.com", username="testuser", hashed_password="xxx")


@pytest.fixture
def client(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_analysis_provider_failure_returns_502(client):
    """When market_provider.get_history raises RuntimeError, should return 502."""
    from app.providers.chain import FallbackChain
    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(
            side_effect=RuntimeError("All providers failed")
        )
        response = client.get("/api/analysis/AAPL?period=1mo")
        assert response.status_code == 502
        assert "unavailable" in response.json()["detail"].lower()
        assert "AAPL" in response.json()["detail"]


def test_get_batch_signals_partial_failure_returns_structured_errors(client):
    """When one symbol fails and another succeeds, return 200 with signals + errors.

    The get_batch_signals handler catches HTTPException (from the 502 path in
    _compute_analysis) and also falls back to a generic 'analysis failed' for any
    other exception, collecting them all into the ``errors`` list while still
    returning 200 with the symbols that succeeded.
    """
    from app.providers.chain import FallbackChain
    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        # AAPL: provider raises RuntimeError -> _compute_analysis raises 502 -> caught
        # GOOG: returns a real-looking DataFrame -> analysis succeeds
        import pandas as pd
        from datetime import datetime
        from app.providers.chain import TaggedValue

        # Need 50+ rows so SMA20/SMA50 don't produce all-NaN series.
        n = 60
        good_df = pd.DataFrame({
            "Open":   [150.0 + i * 0.1 for i in range(n)],
            "High":   [152.0 + i * 0.1 for i in range(n)],
            "Low":    [149.0 + i * 0.1 for i in range(n)],
            "Close":  [151.0 + i * 0.1 for i in range(n)],
            "Volume": [1_000_000 + i * 10_000 for i in range(n)],
        }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

        def get_history_side_effect(symbol, period, interval):
            if symbol == "AAPL":
                raise RuntimeError("All providers failed")
            return TaggedValue(good_df, "yfinance", datetime.utcnow())

        mock_provider.get_history = AsyncMock(side_effect=get_history_side_effect)

        response = client.get("/api/analysis/signals?symbols=AAPL,GOOG&period=1mo")
        assert response.status_code == 200
        data = response.json()
        assert "signals" in data
        assert "errors" in data
        # GOOG should have a valid signal; AAPL should be in errors
        assert len(data["signals"]) == 1
        assert data["signals"][0]["symbol"] == "GOOG"
        assert len(data["errors"]) == 1
        assert data["errors"][0]["symbol"] == "AAPL"
        assert "unavailable" in data["errors"][0]["error"].lower()


def test_get_batch_signals_all_fail_returns_empty_signals_with_errors(client):
    """When all symbols fail, return 200 with empty signals list and populated errors."""
    from app.providers.chain import FallbackChain
    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(
            side_effect=RuntimeError("All providers failed")
        )
        response = client.get("/api/analysis/signals?symbols=INVALD1,INVALD2&period=1mo")
        assert response.status_code == 200
        data = response.json()
        assert data["signals"] == []
        assert len(data["errors"]) == 2
        assert data["errors"][0]["symbol"] == "INVALD1"
        assert data["errors"][1]["symbol"] == "INVALD2"


def _thin_df(n):
    """A valid-shaped OHLCV frame with only ``n`` trading days (e.g. a new IPO)."""
    import pandas as pd
    return pd.DataFrame({
        "Open":   [10.0 + i * 0.1 for i in range(n)],
        "High":   [10.5 + i * 0.1 for i in range(n)],
        "Low":    [9.5 + i * 0.1 for i in range(n)],
        "Close":  [10.2 + i * 0.1 for i in range(n)],
        "Volume": [500_000 + i * 1_000 for i in range(n)],
    }, index=pd.date_range("2026-06-26", periods=n, freq="D"))


def test_get_analysis_recently_listed_returns_422_with_reason(client):
    """A symbol with too few trading days (recent IPO, e.g. SPCX) returns a
    specific 422 reason, never a generic 500/"analysis failed"."""
    from datetime import datetime
    from app.providers.chain import FallbackChain, TaggedValue
    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(
            return_value=TaggedValue(_thin_df(1), "yfinance", datetime.utcnow())
        )
        response = client.get("/api/analysis/SPCX?period=1mo")
        assert response.status_code == 422
        detail = response.json()["detail"]
        assert "SPCX" in detail
        assert "history" in detail.lower()
        # the reason must mention how thin the data is, not be opaque
        assert "1 trading day" in detail


def test_get_batch_signals_thin_history_surfaces_specific_reason(client):
    """In the batch endpoint a recently-listed symbol lands in errors[] with the
    insufficient-history reason while a well-established symbol still succeeds."""
    from datetime import datetime
    from app.providers.chain import FallbackChain, TaggedValue

    good = _thin_df(60)  # plenty of history
    thin = _thin_df(1)   # listed today

    def side_effect(symbol, period, interval):
        return TaggedValue(good if symbol == "AAPL" else thin, "yfinance", datetime.utcnow())

    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(side_effect=side_effect)
        response = client.get("/api/analysis/signals?symbols=AAPL,SPCX&period=1mo")
        assert response.status_code == 200
        data = response.json()
        assert [s["symbol"] for s in data["signals"]] == ["AAPL"]
        assert len(data["errors"]) == 1
        err = data["errors"][0]
        assert err["symbol"] == "SPCX"
        assert "history" in err["error"].lower()
        assert err["error"] != "analysis failed"


def test_get_analysis_includes_rvol_and_volume_spike(client):
    """Analysis response includes indicators.rvol and volume_spike boolean."""
    import pandas as pd
    from datetime import datetime
    from app.providers.chain import FallbackChain, TaggedValue

    n = 60
    # Very high volume to trigger volume_spike (rvol > 2.0)
    df = pd.DataFrame({
        "Open":   [150.0 + i * 0.1 for i in range(n)],
        "High":   [152.0 + i * 0.1 for i in range(n)],
        "Low":    [149.0 + i * 0.1 for i in range(n)],
        "Close":  [151.0 + i * 0.1 for i in range(n)],
        "Volume": [50_000_000 + i * 100_000 for i in range(n)],  # ~50M avg, spike
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

    def side_effect(symbol, period, interval):
        return TaggedValue(df, "yfinance", datetime.utcnow())

    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(side_effect=side_effect)
        response = client.get("/api/analysis/AAPL?period=1mo")
        assert response.status_code == 200
        data = response.json()
        # rvol should be in indicators
        assert "rvol" in data["indicators"]
        assert data["indicators"]["rvol"] is not None
        # volume_spike should be a boolean
        assert "volume_spike" in data
        assert isinstance(data["volume_spike"], bool)


def test_get_analysis_breakout_true_when_within_2pct_and_high_rvol(client):
    """Breakout is true when close is within 2% of 52w high AND rvol > 1.5."""
    import pandas as pd
    from datetime import datetime
    from app.providers.chain import FallbackChain, TaggedValue

    n = 60
    # close = 152 + 0.1*i, at i=59 close = 157.9 (within 2% of 160 since 0.98*160=156.8)
    # For rvol > 1.5 at last bar: need last_vol > 1.5 * avg(last_20_vols)
    # Using Volume = [100M]*50 + [320M]*10:
    #   avg(last 20, indices 40-59) = (10*100M + 10*320M)/20 = 2100M/20 = 105M
    #   last_vol = 320M
    #   rvol = 320/105 ≈ 3.05 > 1.5 ✓
    df = pd.DataFrame({
        "Open":   [157.0 + i * 0.1 for i in range(n)],
        "High":   [159.0 + i * 0.1 for i in range(n)],
        "Low":    [156.0 + i * 0.1 for i in range(n)],
        "Close":  [152.0 + i * 0.1 for i in range(n)],  # close at i=59 = 157.9
        "Volume": [100_000_000 for _ in range(50)] + [320_000_000 for _ in range(10)],
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

    n_1y = 252
    high_52w_df = pd.DataFrame({
        "Open":   [140.0 + i * 0.05 for i in range(n_1y)],
        "High":   [160.0 for i in range(n_1y)],  # 52w high = 160
        "Low":    [130.0 + i * 0.03 for i in range(n_1y)],
        "Close":  [150.0 + i * 0.02 for i in range(n_1y)],
        "Volume": [20_000_000 for i in range(n_1y)],
    }, index=pd.date_range("2023-01-01", periods=n_1y, freq="D"))

    def side_effect(symbol, period, interval):
        if period == "1y":
            return TaggedValue(high_52w_df, "yfinance", datetime.utcnow())
        return TaggedValue(df, "yfinance", datetime.utcnow())

    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(side_effect=side_effect)
        response = client.get("/api/analysis/AAPL?period=1mo")
        assert response.status_code == 200
        data = response.json()
        # 52w metrics should be present
        assert data["indicators"]["high_52w"] == 160.0
        assert data["indicators"]["low_52w"] is not None
        assert data["indicators"]["pct_from_52w_high"] is not None
        # breakout should be true
        assert "breakout" in data
        assert data["breakout"] is True


def test_get_analysis_breakout_false_when_1y_fetch_fails(client):
    """When 1y history fetch fails, 52w fields are None and breakout is false (graceful degradation)."""
    import pandas as pd
    from datetime import datetime
    from app.providers.chain import FallbackChain, TaggedValue

    n = 60
    df = pd.DataFrame({
        "Open":   [150.0 + i * 0.1 for i in range(n)],
        "High":   [152.0 + i * 0.1 for i in range(n)],
        "Low":    [149.0 + i * 0.1 for i in range(n)],
        "Close":  [151.0 + i * 0.1 for i in range(n)],
        "Volume": [1_000_000 + i * 10_000 for i in range(n)],
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

    def side_effect(symbol, period, interval):
        if period == "1y":
            raise RuntimeError("1y data unavailable")
        return TaggedValue(df, "yfinance", datetime.utcnow())

    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(side_effect=side_effect)
        response = client.get("/api/analysis/AAPL?period=1mo")
        assert response.status_code == 200
        data = response.json()
        # 52w fields should be None due to graceful degradation
        assert data["indicators"]["high_52w"] is None
        assert data["indicators"]["low_52w"] is None
        assert data["indicators"]["pct_from_52w_high"] is None
        # breakout should be false
        assert data["breakout"] is False


def test_get_analysis_near_52w_high_no_volume_confirmation(client):
    """When price is within 2% of 52w high but rvol <= 1.5 (no breakout),
    append 'Near 52-week high (no volume confirmation)' reason with NO score change."""
    import pandas as pd
    from datetime import datetime
    from app.providers.chain import FallbackChain, TaggedValue

    n = 60
    # close = 155 + 0.05*i, at i=59 close = 157.95 (>= 156.8 = 0.98*160 ✓)
    # rvol = 1.0 (constant 10M volume, 20d avg = 10M), so breakout = False
    df = pd.DataFrame({
        "Open":   [155.5 + i * 0.05 for i in range(n)],
        "High":   [157.5 + i * 0.05 for i in range(n)],
        "Low":    [154.5 + i * 0.05 for i in range(n)],
        "Close":  [155.0 + i * 0.05 for i in range(n)],  # close at i=59 = 157.95
        "Volume": [10_000_000 for _ in range(n)],  # constant, rvol = 1.0
    }, index=pd.date_range("2024-01-01", periods=n, freq="D"))

    n_1y = 252
    high_52w_df = pd.DataFrame({
        "Open":   [140.0 + i * 0.05 for i in range(n_1y)],
        "High":   [160.0 for i in range(n_1y)],  # 52w high = 160
        "Low":    [130.0 + i * 0.03 for i in range(n_1y)],
        "Close":  [150.0 + i * 0.02 for i in range(n_1y)],
        "Volume": [20_000_000 for i in range(n_1y)],
    }, index=pd.date_range("2023-01-01", periods=n_1y, freq="D"))

    def side_effect(symbol, period, interval):
        if period == "1y":
            return TaggedValue(high_52w_df, "yfinance", datetime.utcnow())
        return TaggedValue(df, "yfinance", datetime.utcnow())

    with patch("app.routes.analysis.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(side_effect=side_effect)
        response = client.get("/api/analysis/AAPL?period=1mo")
        assert response.status_code == 200
        data = response.json()
        # breakout should be false (rvol=1.0, not > 1.5)
        assert data["breakout"] is False
        # 52w metrics should be present
        assert data["indicators"]["high_52w"] == 160.0
        # near-52w-high reason should be present (no score change, just reason)
        reasons_lower = [r.lower() for r in data["reasons"]]
        assert any("near 52-week high" in r for r in reasons_lower)
        assert not any("breakout on volume" in r for r in reasons_lower)


# ------------------------------------------------------------------
# Divergence detection tests
# ------------------------------------------------------------------

def _flat_rsi(length: int, value: float) -> pd.Series:
    """Return a constant RSI series of the given length."""
    return pd.Series([value] * length)


class TestDetectDivergenceBullish:
    """Price makes a lower low while RSI makes a higher low → bullish."""

    def test_bullish_divergence_detected(self):
        from app.services.signals import detect_divergence  # lazy: avoid pandas_ta at module load
        # Price: high → drop → slight recovery, then new lower low
        # RSI: rising at the second low
        rsi_vals = (
            [50.0] * 20 +
            [40.0, 42.0, 44.0, 46.0, 48.0,
             45.0, 43.0, 41.0,
             47.0, 50.0, 53.0]
        )
        close_vals = (
            [100.0] * 20 +
            [95.0, 93.0, 91.0, 90.0,
             92.0, 91.0, 90.0,
             88.0, 87.0, 86.0]
        )
        close = pd.Series(close_vals)
        rsi = pd.Series(rsi_vals)
        result = detect_divergence(close, rsi)
        assert result == "bullish"

    def test_bullish_divergence_score_and_reason(self):
        from app.services.signals import score_signals  # lazy
        score, reasons = score_signals(
            bias=None, macd_hist=None, kdj_k=None, kdj_d=None,
            vol_ratio=None, rvol=None, breakout=False, high_52w=None,
            divergence="bullish",
        )
        assert score == 0.25
        assert any("bullish" in r.lower() and "divergence" in r.lower() for r in reasons)


class TestDetectDivergenceBearish:
    """Price makes a higher high while RSI makes a lower high → bearish."""

    def test_bearish_divergence_detected(self):
        from app.services.signals import detect_divergence  # lazy
        # Price: rise → pullback → new higher high; RSI declining at each high
        close_vals = (
            [80.0] * 20 +
            [82.0, 84.0, 86.0, 88.0,
             87.0, 86.0, 85.0,
             89.0, 91.0, 93.0]
        )
        rsi_vals = (
            [50.0] * 20 +
            [58.0, 60.0, 62.0, 64.0,
             63.0, 61.0, 60.0,
             58.0, 56.0, 54.0]
        )
        close = pd.Series(close_vals)
        rsi = pd.Series(rsi_vals)
        result = detect_divergence(close, rsi)
        assert result == "bearish"

    def test_bearish_divergence_score_and_reason(self):
        from app.services.signals import score_signals  # lazy
        score, reasons = score_signals(
            bias=None, macd_hist=None, kdj_k=None, kdj_d=None,
            vol_ratio=None, rvol=None, breakout=False, high_52w=None,
            divergence="bearish",
        )
        assert score == -0.25
        assert any("bearish" in r.lower() and "divergence" in r.lower() for r in reasons)


class TestDetectDivergenceNone:
    """Series with no divergence → None."""

    def test_no_divergence_returns_none(self):
        from app.services.signals import detect_divergence  # lazy
        # Steady uptrend: price and RSI both rising → no divergence
        close = pd.Series([100.0 + i for i in range(30)])
        rsi = pd.Series([50.0 + i * 0.5 for i in range(30)])
        result = detect_divergence(close, rsi, lookback=30, order=3)
        assert result is None

    def test_flat_price_and_rsi_returns_none(self):
        from app.services.signals import detect_divergence  # lazy
        # Constant price and RSI → no divergence
        close = pd.Series([100.0] * 30)
        rsi = pd.Series([50.0] * 30)
        result = detect_divergence(close, rsi, lookback=30, order=3)
        assert result is None


class TestDetectDivergenceEdgeCases:
    """Edge cases: insufficient data."""

    def test_fewer_than_2_pivots_returns_none(self):
        from app.services.signals import detect_divergence  # lazy
        # Very short series: can't find 2 pivots with order=3
        close = pd.Series([100.0, 101.0, 99.0, 102.0, 98.0])
        rsi = pd.Series([50.0, 52.0, 48.0, 54.0, 46.0])
        result = detect_divergence(close, rsi, lookback=5, order=3)
        assert result is None

    def test_rsi_all_nan_returns_none(self):
        from app.services.signals import detect_divergence  # lazy
        close = pd.Series([100.0 + i for i in range(30)])
        rsi = pd.Series([None] * 30)
        result = detect_divergence(close, rsi, lookback=30, order=3)
        assert result is None

    def test_series_shorter_than_lookback_returns_none(self):
        from app.services.signals import detect_divergence  # lazy
        close = pd.Series([100.0 + i for i in range(10)])
        rsi = pd.Series([50.0] * 10)
        result = detect_divergence(close, rsi, lookback=60, order=3)
        assert result is None

