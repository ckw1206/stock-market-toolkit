"""Regression: NaN Close rows from a provider must never leave the chain.

yfinance intermittently returns a trailing partial row with NaN Close.
Downstream, that NaN reaches JSON responses (starlette renders with
allow_nan=False -> the whole request 500s, e.g. 'Failed to fetch signals
(HTTP 500)') and quote lookups that take Close.iloc[-1] (portfolio
last_price / paper trade pricing).
"""

import numpy as np
import pandas as pd
import pytest

from app.providers.chain import FallbackChain


def _df_with_trailing_nan_close(n: int = 10) -> pd.DataFrame:
    df = pd.DataFrame(
        {
            "Open": [100.0 + i for i in range(n)],
            "High": [101.0 + i for i in range(n)],
            "Low": [99.0 + i for i in range(n)],
            "Close": [100.5 + i for i in range(n)],
            "Volume": [1_000_000.0] * n,
        },
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
    )
    df.iloc[-1, df.columns.get_loc("Close")] = np.nan
    return df


class StubProvider:
    name = "yfinance"  # matches the "default" chain in registry.py

    def __init__(self, df: pd.DataFrame):
        self._df = df

    async def get_history(self, symbol, period, interval, lookback_extra=0):
        return self._df


@pytest.mark.asyncio
async def test_chain_drops_nan_close_rows():
    chain = FallbackChain([StubProvider(_df_with_trailing_nan_close())])
    result = await chain.get_history("TEST", period="1mo", interval="1d")
    df = result.value
    assert not df["Close"].isna().any()
    assert float(df["Close"].iloc[-1]) == 108.5  # last valid close, not NaN


@pytest.mark.asyncio
async def test_chain_all_nan_close_treated_as_no_data():
    df = _df_with_trailing_nan_close()
    df["Close"] = np.nan
    chain = FallbackChain([StubProvider(df)])
    with pytest.raises(RuntimeError):  # falls through the chain like empty data
        await chain.get_history("TEST", period="1mo", interval="1d")
