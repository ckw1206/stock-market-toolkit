from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class StockDataResponse(BaseModel):
    symbol: str
    period: str
    cached_at: str = ""
    source: str = ""
    as_of: Optional[datetime] = None
    timestamp: list[str]
    open: list[float | None]
    high: list[float | None]
    low: list[float | None]
    close: list[float | None]
    volume: list[int | None]


class IndicatorsResponse(BaseModel):
    symbol: str
    period: str
    cached_at: str = ""
    timestamp: list[str]
    sma20: list[float | None]
    sma50: list[float | None]
    sma200: list[float | None]
    ema12: list[float | None]
    ema26: list[float | None]
    rsi: list[float | None]
    macd: list[float | None]
    macd_signal: list[float | None]
    macd_hist: list[float | None]
    bb_upper: list[float | None]
    bb_middle: list[float | None]
    bb_lower: list[float | None]
    atr: list[float | None]


class StockInfoResponse(BaseModel):
    symbol: str
    cached_at: str = ""
    source: str = ""
    as_of: Optional[datetime] = None
    short_name: str
    long_name: Optional[str]
    sector: Optional[str]
    industry: Optional[str]
    price: float
    previous_close: Optional[float] = None
    currency: Optional[str]
    market_cap: Optional[int]
    sharesOutstanding: Optional[int]
    trailing_pe: Optional[float]
    forward_pe: Optional[float]
    dividend_yield: Optional[float]
    avg_volume: Optional[int]
    beta: Optional[float]
    week_52_high: Optional[float]
    week_52_low: Optional[float]


class CompareRequest(BaseModel):
    symbols: list[str] = Field(..., min_length=2, max_length=5)
    period: str = "1mo"


class CompareStockData(BaseModel):
    symbol: str
    timestamp: list[str]
    close: list[float | None]
    volume: list[int | None]


class CompareResponse(BaseModel):
    stocks: list[CompareStockData]
