import pytest
from unittest.mock import AsyncMock, patch


@pytest.fixture(autouse=True)
def _no_real_earnings_lookups():
    """Prevent tests from making real yfinance network calls for earnings dates.

    ``compute_analysis_impl`` calls ``get_next_earnings_date`` on every
    invocation; most tests only care about price/indicator behavior and mock
    the OHLCV provider but not this call, which would otherwise hit the real
    yfinance API. Tests that specifically exercise earnings behavior patch
    ``app.services.signals.get_next_earnings_date`` themselves in a nested
    `with` block, which takes precedence over this default for its duration.
    """
    with patch("app.services.signals.get_next_earnings_date", AsyncMock(return_value=None)):
        yield
