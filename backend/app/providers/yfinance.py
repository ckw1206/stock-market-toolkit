"""YFinance implementation of market data and fundamentals providers."""

import asyncio
from datetime import datetime

import yfinance as yf
import pandas as pd
import logging

from app.services.cache import cached, cache_key

log = logging.getLogger(__name__)


def _to_epoch(value) -> int | None:
    """Normalize a yfinance publish time to a unix-epoch int (seconds).

    The current yfinance news schema returns ``content.pubDate`` as an
    ISO-8601 string (e.g. ``"2026-06-27T12:00:00Z"``); the legacy schema
    returned ``providerPublishTime`` as a unix-epoch int. ``NewsArticle.
    publishedAt`` is typed ``int`` and the frontend expects epoch seconds, so
    coerce both forms (and drop anything unparseable) here — otherwise an ISO
    string fails response-model validation and 500s the whole /news endpoint.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            # fromisoformat rejects a trailing 'Z' before Python 3.11.
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return int(dt.timestamp())
        except ValueError:
            return None
    return None


# TTLs in seconds
OHLCV_TTL = 300  # 5 min for intraday/daily OHLCV
INFO_TTL = 3600  # 1 hr for stock info

NEWS_TTL = 900  # 15 min


class YFinanceMarketDataProvider:
    """Market data provider backed by yfinance, with caching."""

    name = "yfinance"

    def history(self, symbol: str, period: str, interval: str) -> pd.DataFrame:
        """Synchronous history fetch (used internally)."""
        ticker = yf.Ticker(symbol.upper())
        return ticker.history(period=period, interval=interval, auto_adjust=True)

    def info(self, symbol: str) -> dict:
        """Synchronous info fetch (used internally)."""
        ticker = yf.Ticker(symbol.upper())
        return ticker.info or {}

    async def get_history(
        self, symbol: str, period: str, interval: str, lookback_extra: int = 0
    ) -> pd.DataFrame:
        """Cached async history fetch.

        Parameters
        ----------
        lookback_extra:
            When > 0, fetch ``lookback_extra`` additional calendar days of
            lookback beyond the requested ``period`` so callers can compute
            rolling indicators that need historical warm-up. The returned
            DataFrame contains the padded rows; callers must trim them before
            serialising the response.
        """
        key_extra = f":le{lookback_extra}" if lookback_extra else ""

        async def loader() -> pd.DataFrame:
            df = await asyncio.to_thread(
                self._history_with_extra, symbol, period, interval, lookback_extra
            )
            return df

        key = cache_key("ohlcv", symbol, period, interval) + key_extra
        return await cached(key, OHLCV_TTL, loader)

    def _history_with_extra(
        self, symbol: str, period: str, interval: str, lookback_extra: int
    ) -> pd.DataFrame:
        """Fetch history, optionally extending the start date by lookback_extra days."""
        ticker = yf.Ticker(symbol.upper())
        if lookback_extra <= 0:
            return ticker.history(period=period, interval=interval, auto_adjust=True)

        # Compute a start date by going back lookback_extra calendar days
        # from "now" and also accounting for the requested period.
        # period_len maps the period string to an approximate duration in days.
        period_len = {
            "1d": 1,
            "5d": 5,
            "1w": 7,
            "1mo": 30,
            "3mo": 90,
            "6mo": 180,
            "1y": 365,
            "2y": 730,
            "5y": 1825,
            "max": 36500,
        }.get(period, 30)

        end = pd.Timestamp.utcnow()
        start = end - pd.Timedelta(days=period_len + lookback_extra)
        return ticker.history(start=start.isoformat(), end=end.isoformat(), interval=interval, auto_adjust=True)

    async def get_info(self, symbol: str) -> dict:
        """Cached async info fetch."""
        key = cache_key("info", symbol)

        async def loader() -> dict:
            return await asyncio.to_thread(self.info, symbol)

        return await cached(key, INFO_TTL, loader)

    def news(self, symbol: str) -> list[dict]:
        raw = yf.Ticker(symbol.upper()).news or []
        out = []
        for n in raw[:10]:
            c = n.get("content", n)
            out.append({
                "title":       c.get("title"),
                "publisher":   (c.get("provider") or {}).get("displayName") or n.get("publisher"),
                "link":        (c.get("canonicalUrl") or {}).get("url") or n.get("link"),
                "publishedAt": _to_epoch(c.get("pubDate") or n.get("providerPublishTime")),
            })
        return [x for x in out if x["title"] and x["link"]]

    async def get_news(self, symbol: str) -> list[dict]:
        key = cache_key("news", symbol)

        async def loader() -> list[dict]:
            return await asyncio.to_thread(self.news, symbol)

        return await cached(key, NEWS_TTL, loader)


FUNDAMENTALS_TTL = 86400  # 24h

# ── yfinance row-label → canonical key mappings ──────────────────────────
_INCOME_FIELDS = {
    "Total Revenue": "total_revenue",
    "Cost of Revenue": "cost_of_revenue",
    "Gross Profit": "gross_profit",
    "Operating Income": "operating_income",
    "Net Income": "net_income",
    "Net Income from Continuing Operations": "net_income",
    "Basic EPS": "basic_eps",
    "Diluted EPS": "diluted_eps",
    "Weighted Average Shs Out": "weighted_shares_outstanding",
}

_BALANCE_FIELDS = {
    "Total Assets": "total_assets",
    "Current Assets": "current_assets",
    "Current Liabilities": "current_liabilities",
    "Long Term Debt": "long_term_debt",
    "Total Equity Gross Minority Interest": "total_equity",
    "Stockholders Equity": "total_equity",
}

_CASHFLOW_FIELDS = {
    "Operating Cash Flow": "operating_cash_flow",
    "Free Cash Flow": "free_cash_flow",
}


def _extract_row(df: pd.DataFrame, field_map: dict, col_idx: int) -> dict:
    """Extract values from a yfinance DataFrame at column *col_idx*.

    Returns a dict mapping canonical field names to float values.
    """
    result = {}
    if df is None or df.empty or col_idx >= len(df.columns):
        return result
    for label, canonical in field_map.items():
        try:
            series = df.loc[label]
            val = series.iloc[col_idx] if hasattr(series, "iloc") else series
            if isinstance(val, pd.Series):
                val = val.iloc[0]
            if pd.notna(val):
                result[canonical] = float(val)
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return result


class YFinanceFundamentalsProvider:
    """Fundamentals provider backed by yfinance, with caching."""

    name = "yfinance"

    FUNDAMENTALS_TTL = 3600  # 1 hr

    def income_statement(self, symbol: str) -> pd.DataFrame:
        return yf.Ticker(symbol.upper()).income_stmt

    def balance_sheet(self, symbol: str) -> pd.DataFrame:
        return yf.Ticker(symbol.upper()).balance_sheet

    def cash_flow(self, symbol: str) -> pd.DataFrame:
        return yf.Ticker(symbol.upper()).cashflow

    def dividends(self, symbol: str) -> pd.Series:
        return yf.Ticker(symbol.upper()).dividends

    async def get_fundamentals_dict(self, symbol: str) -> dict:
        """Return ``{current: dict, prior: dict}`` with canonical field names.

        Cached with ``FUNDAMENTALS_TTL`` (24 h).
        """
        key = cache_key("fundamentals", symbol)

        async def loader() -> dict:
            def _fetch():
                t = yf.Ticker(symbol.upper())
                return t.income_stmt, t.balance_sheet, t.cashflow

            is_df, bs_df, cf_df = await asyncio.to_thread(_fetch)
            current = {}
            prior = {}

            for df, fmap in [
                (is_df, _INCOME_FIELDS),
                (bs_df, _BALANCE_FIELDS),
                (cf_df, _CASHFLOW_FIELDS),
            ]:
                current.update(_extract_row(df, fmap, 0))
                if df is not None and len(df.columns) > 1:
                    prior.update(_extract_row(df, fmap, 1))

            return {"current": current, "prior": prior}

        return await cached(key, FUNDAMENTALS_TTL, loader)

    async def get_income_statement(self, symbol: str) -> pd.DataFrame:
        key = cache_key("income_stmt", symbol)

        async def loader() -> pd.DataFrame:
            return await asyncio.to_thread(self.income_statement, symbol)

        return await cached(key, self.FUNDAMENTALS_TTL, loader)

    async def get_balance_sheet(self, symbol: str) -> pd.DataFrame:
        key = cache_key("balance_sheet", symbol)

        async def loader() -> pd.DataFrame:
            return await asyncio.to_thread(self.balance_sheet, symbol)

        return await cached(key, self.FUNDAMENTALS_TTL, loader)

    async def get_cash_flow(self, symbol: str) -> pd.DataFrame:
        key = cache_key("cash_flow", symbol)

        async def loader() -> pd.DataFrame:
            return await asyncio.to_thread(self.cash_flow, symbol)

        return await cached(key, self.FUNDAMENTALS_TTL, loader)

    async def get_dividends(self, symbol: str) -> pd.Series:
        key = cache_key("dividends", symbol)

        async def loader() -> pd.Series:
            return await asyncio.to_thread(self.dividends, symbol)

        return await cached(key, self.FUNDAMENTALS_TTL, loader)
