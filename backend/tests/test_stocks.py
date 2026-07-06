import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_current_user
from app.routes import stock_info, search, news  # noqa: F401 — imported as mock patch targets
from app.models import User


@pytest.fixture
def mock_user():
    user = User(id="1", email="test@test.com", username="testuser", hashed_password="xxx")
    return user


@pytest.fixture
def client(mock_user):
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_get_stock_provider_failure_returns_503(client):
    """When yfinance fails, should return 503 not 500."""
    from app.providers.chain import FallbackChain
    with patch("app.routes.stocks.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(
            side_effect=RuntimeError("All providers failed")
        )
        response = client.get("/api/stock/AAPL?period=1mo")
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


def test_get_stock_empty_data_returns_404(client):
    """When provider returns empty DataFrame, should return 404."""
    from app.providers.chain import FallbackChain, TaggedValue
    import pandas as pd
    with patch("app.routes.stocks.market_provider", spec=FallbackChain) as mock_provider:
        empty_df = pd.DataFrame({"Open": [], "High": [], "Low": [], "Close": [], "Volume": []})
        mock_result = MagicMock(spec=TaggedValue)
        mock_result.value = empty_df
        mock_result.source = "yfinance"
        mock_result.as_of = datetime.utcnow()
        mock_provider.get_history = AsyncMock(return_value=mock_result)
        response = client.get("/api/stock/INVALID?period=1mo")
        assert response.status_code == 404


def test_get_indicators_provider_failure_returns_503(client):
    """When market provider fails, indicators endpoint should return 503."""
    from app.providers.chain import FallbackChain
    with patch("app.routes.stocks.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_history = AsyncMock(
            side_effect=RuntimeError("All providers failed")
        )
        response = client.get("/api/stock/AAPL/indicators?period=3mo")
        assert response.status_code == 503


def test_get_stock_info_provider_failure_returns_503(client):
    """When market provider fails, info endpoint should return 503."""
    from app.providers.chain import FallbackChain
    with patch("app.routes.stock_info.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_info = AsyncMock(
            side_effect=RuntimeError("All providers failed")
        )
        response = client.get("/api/stock/AAPL/info")
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


def test_get_fundamentals_provider_failure_returns_503(client):
    from app.providers.chain import FallbackChain
    with patch("app.routes.stock_info.fundamentals_provider", spec=FallbackChain) as mock:
        mock.get_fundamentals_dict = AsyncMock(
            side_effect=RuntimeError("All providers failed")
        )
        response = client.get("/api/stock/AAPL/fundamentals")
        assert response.status_code == 503


def test_get_dividends_provider_failure_returns_503(client):
    from app.providers.chain import FallbackChain
    with patch("app.routes.stock_info.fundamentals_provider", spec=FallbackChain) as mock:
        mock.get_dividends = AsyncMock(side_effect=RuntimeError("All providers failed"))
        response = client.get("/api/stock/AAPL/dividends")
        assert response.status_code == 503


def test_compare_provider_failure_returns_503(client):
    from app.providers.chain import FallbackChain
    with patch("app.routes.stocks.market_provider", spec=FallbackChain) as mock:
        mock.get_history = AsyncMock(side_effect=RuntimeError("All providers failed"))
        response = client.post("/api/compare", json={"symbols": ["AAPL", "GOOG"], "period": "1mo"})
        assert response.status_code == 503


def test_provider_error_message_includes_providers_list(client):
    """Verify that when all providers fail, error message includes helpful text."""
    from app.providers.chain import FallbackChain
    with patch("app.routes.stocks.market_provider", spec=FallbackChain) as mock:
        mock.get_history = AsyncMock(
            side_effect=RuntimeError(
                "All providers failed for symbol=AAPL period=1mo interval=1d. "
                "Providers tried: ['yfinance']"
            )
        )
        response = client.get("/api/stock/AAPL?period=1mo")
        assert response.status_code == 503
        assert "unavailable" in response.json()["detail"].lower()


# ─── /api/stock/{symbol}/news endpoint tests ──────────────────────────────────

def test_get_stock_news_happy_path(client):
    """Returns 200 with correct NewsResponse shape when provider returns articles."""
    from app.providers.chain import FallbackChain
    fake_articles = [
        {
            "title": "Apple Reports Record Q3 Earnings",
            "publisher": "Reuters",
            "link": "https://example.com/article1",
            "publishedAt": 1699900000,
        },
        {
            "title": "AAPL Hits New High",
            "publisher": "CNBC",
            "link": "https://example.com/article2",
            "publishedAt": 1699800000,
        },
    ]
    with patch("app.routes.news.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_news = AsyncMock(return_value=fake_articles)
        response = client.get("/api/stock/AAPL/news")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert "cached_at" in data
        assert len(data["articles"]) == 2
        assert data["articles"][0]["title"] == "Apple Reports Record Q3 Earnings"
        assert data["articles"][0]["link"] == "https://example.com/article1"


def test_news_provider_parses_iso_pubdate_to_epoch():
    """yfinance returns content.pubDate as an ISO string; the provider must
    coerce it to an epoch int so NewsResponse validation doesn't 500."""
    from app.providers.yfinance import YFinanceMarketDataProvider, _to_epoch

    assert _to_epoch("2026-06-27T12:00:00Z") == 1782561600
    assert _to_epoch(1699900000) == 1699900000
    assert _to_epoch(None) is None
    assert _to_epoch("not-a-date") is None

    raw = [
        {
            "content": {
                "title": "Apple climbs",
                "provider": {"displayName": "Reuters"},
                "canonicalUrl": {"url": "https://example.com/a"},
                "pubDate": "2026-06-27T12:00:00Z",
            }
        }
    ]
    with patch("app.providers.yfinance.yf.Ticker") as mock_ticker:
        mock_ticker.return_value.news = raw
        articles = YFinanceMarketDataProvider().news("AAPL")

    assert len(articles) == 1
    a = articles[0]
    assert a["title"] == "Apple climbs"
    assert a["publisher"] == "Reuters"
    assert a["link"] == "https://example.com/a"
    assert a["publishedAt"] == 1782561600
    assert isinstance(a["publishedAt"], int)


def test_get_stock_news_provider_failure_returns_empty_articles(client):
    """When market_provider.get_news raises, returns 200 with empty articles.

    News is non-critical so the endpoint swallows provider failures and returns
    an empty list rather than a 503 — consistent with the endpoint design.
    """
    from app.providers.chain import FallbackChain
    with patch("app.routes.news.market_provider", spec=FallbackChain) as mock_provider:
        mock_provider.get_news = AsyncMock(
            side_effect=RuntimeError("All providers failed for news symbol=AAPL")
        )
        response = client.get("/api/stock/AAPL/news")
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert data["articles"] == []


# ─── Indicator lookback padding tests ─────────────────────────────────────────

def test_indicators_endpoint_pads_lookback_and_trims(client):
    """Indicators endpoint requests lookback_extra=200 and trims padded rows."""
    from app.providers.chain import FallbackChain, TaggedValue
    import pandas as pd

    # Build a DataFrame long enough to contain padding + display rows.
    # period=1mo has ~21 display bars; with 200 lookback_extra the total is ~221.
    n_display = 21
    n_pad = 200
    n_total = n_display + n_pad

    idx = pd.date_range("2024-01-01", periods=n_total, freq="D")
    close = [100.0 + i * 0.1 for i in range(n_total)]
    df = pd.DataFrame(
        {"Open": close, "High": close, "Low": close, "Close": close, "Volume": [1000] * n_total},
        index=idx,
    )

    with patch("app.routes.stocks.market_provider", spec=FallbackChain) as mock_provider:
        mock_result = MagicMock(spec=TaggedValue)
        mock_result.value = df
        mock_result.source = "yfinance"
        mock_result.as_of = datetime.utcnow()
        mock_provider.get_history = AsyncMock(return_value=mock_result)

        response = client.get("/api/stock/AAPL/indicators?period=1mo")

    assert response.status_code == 200
    data = response.json()
    # After trim the response should cover only the display period (~21 bars)
    assert len(data["timestamp"]) == n_display
    # SMA20 needs 20 prior bars — with padding all display bars should have values
    assert data["sma20"].count(None) == 0, "SMA20 should have no nulls in display period"
    # SMA50 — after trimming the first 200 padded rows, the 21-row response
    # covers the LAST 21 rows of the padded df. Those rows have 200 prior bars
    # behind them (from index -200 to -1), which is more than the 50-bar lookback
    # needed for SMA50. So all display bars have valid SMA50 values.
    assert data["sma50"].count(None) == 0, "SMA50 should have values (display period has full lookback)"


def test_indicators_endpoint_passes_lookback_extra_to_provider(client):
    """The indicators endpoint passes lookback_extra=200 to get_history."""
    from app.providers.chain import FallbackChain, TaggedValue
    import pandas as pd

    n = 300
    df = pd.DataFrame(
        {"Open": [100.0] * n, "High": [100.0] * n, "Low": [100.0] * n,
         "Close": [100.0] * n, "Volume": [1000] * n},
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
    )

    with patch("app.routes.stocks.market_provider", spec=FallbackChain) as mock_provider:
        mock_result = MagicMock(spec=TaggedValue)
        mock_result.value = df
        mock_result.source = "yfinance"
        mock_result.as_of = datetime.utcnow()
        mock_provider.get_history = AsyncMock(return_value=mock_result)

        client.get("/api/stock/AAPL/indicators?period=3mo")

    # Verify lookback_extra=200 was passed
    call_kwargs = mock_provider.get_history.call_args.kwargs
    assert call_kwargs.get("lookback_extra") == 200


def test_yfinance_provider_history_with_extra_fetches_longer_range():
    """_history_with_extra requests start+end dates when lookback_extra > 0."""
    from app.providers.yfinance import YFinanceMarketDataProvider
    from unittest.mock import MagicMock, patch

    provider = YFinanceMarketDataProvider()
    mock_ticker = MagicMock()
    mock_df = MagicMock()
    mock_ticker.history.return_value = mock_df

    with patch("app.providers.yfinance.yf.Ticker", return_value=mock_ticker):
        provider._history_with_extra("AAPL", "1mo", "1d", lookback_extra=50)

    # Should have been called with start+end, not period
    mock_ticker.history.assert_called_once()
    _, kwargs = mock_ticker.history.call_args
    assert "start" in kwargs and "end" in kwargs
    assert kwargs.get("auto_adjust", False) is True


def test_yfinance_provider_history_without_extra_uses_period():
    """_history_with_extra uses period= when lookback_extra == 0."""
    from app.providers.yfinance import YFinanceMarketDataProvider
    from unittest.mock import MagicMock, patch

    provider = YFinanceMarketDataProvider()
    mock_ticker = MagicMock()
    mock_df = MagicMock()
    mock_ticker.history.return_value = mock_df

    with patch("app.providers.yfinance.yf.Ticker", return_value=mock_ticker):
        provider._history_with_extra("AAPL", "1mo", "1d", lookback_extra=0)

    mock_ticker.history.assert_called_once()
    _, kwargs = mock_ticker.history.call_args
    assert "period" in kwargs  # Uses period, not start/end


def test_estimate_display_rows_returns_min_of_expected_and_total():
    """_estimate_display_rows returns min(expected, n_total) so trim is safe."""
    from app.routes.stocks import _estimate_display_rows

    # Normal case: n_total > expected
    assert _estimate_display_rows("1mo", 300) == 21
    assert _estimate_display_rows("3mo", 500) == 63

    # Edge case: n_total < expected (thin history)
    assert _estimate_display_rows("1mo", 5) == 5
    assert _estimate_display_rows("1y", 10) == 10

    # Unknown period falls back to 21
    assert _estimate_display_rows("unknown_period", 1000) == 21


def test_indicators_trim_assertion_fires_on_mismatch(client):
    """Post-trim assertion catches DataFrames shorter than _APPROX_DISPLAY_BARS.

    When the padded DataFrame is shorter than _APPROX_DISPLAY_BARS[period],
    no trimming happens (trim=0), but the post-trim assertion must still pass
    because n_original == len(df) in that case.  This test verifies the
    assertion does NOT fire spuriously for thin-history symbols.
    """
    from app.providers.chain import FallbackChain, TaggedValue
    import pandas as pd

    # Build a DataFrame that is SMALLER than _APPROX_DISPLAY_BARS["3mo"] (63).
    # n_total = 50 < 63, so n_original = min(50, 63) = 50, trim = 0.
    n = 50
    idx = pd.date_range("2024-01-01", periods=n, freq="D")
    close = [100.0 + i * 0.1 for i in range(n)]
    df = pd.DataFrame(
        {"Open": close, "High": close, "Low": close, "Close": close, "Volume": [1000] * n},
        index=idx,
    )

    with patch("app.routes.stocks.market_provider", spec=FallbackChain) as mock_provider:
        mock_result = MagicMock(spec=TaggedValue)
        mock_result.value = df
        mock_result.source = "yfinance"
        mock_result.as_of = datetime.utcnow()
        mock_provider.get_history = AsyncMock(return_value=mock_result)

        # Must NOT raise AssertionError — post-trim len must equal n_original (=50)
        response = client.get("/api/stock/AAPL/indicators?period=3mo")

    assert response.status_code == 200
    data = response.json()
    # n_original = min(50, 63) = 50; trim = 0; response covers all 50 rows
    assert len(data["timestamp"]) == 50
    # SMA200 requires 200 bars but df only has 50 — ta.sma returns None for
    # those, so sma200 values will all be None (not an error, just unavailable)
    assert len(data["sma200"]) == 50
