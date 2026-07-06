"""Provider abstraction layer - abstract interfaces."""

from typing import Protocol, runtime_checkable
import pandas as pd


@runtime_checkable
class MarketDataProvider(Protocol):
    """Protocol for market data providers (price history, info)."""

    def history(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        """Return OHLCV DataFrame with columns [Open, High, Low, Close, Volume]."""
        ...

    def info(self, symbol: str) -> dict:
        """Return a normalized info dict (shortName, price, sector, etc.)."""
        ...

    async def get_history(
        self, symbol: str, period: str, interval: str, lookback_extra: int = 0
    ) -> pd.DataFrame:
        """Return cached OHLCV DataFrame. Fallback: calls history().

        Parameters
        ----------
        lookback_extra:
            Request *extra* rows of lookback history beyond the display period.
            The returned DataFrame will contain ``lookback_extra`` additional
            rows prepended to the display period. Callers are responsible for
            trimming those rows before returning data to the client.
            Ignored when 0 (the default).
        """
        ...

    async def get_info(self, symbol: str) -> dict:
        """Return a cached normalized info dict. Fallback: calls info()."""
        ...


@runtime_checkable
class FundamentalsProvider(Protocol):
    """Protocol for fundamental data providers (income, balance, cash flow, dividends)."""

    def income_statement(self, symbol: str) -> pd.DataFrame: ...

    def balance_sheet(self, symbol: str) -> pd.DataFrame: ...

    def cash_flow(self, symbol: str) -> pd.DataFrame: ...

    def dividends(self, symbol: str) -> pd.DataFrame: ...
