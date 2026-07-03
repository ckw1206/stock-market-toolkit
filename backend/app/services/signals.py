"""Pure signal computation — shared by the analysis route and the alert checker."""

import math
from typing import TypedDict

import pandas_ta as ta

from app.providers import market_provider
from app.utils.numeric import _clean


class SignalAnalysisError(Exception):
    """Base class for signal analysis errors."""
    pass


class ProviderUnavailableError(SignalAnalysisError):
    """Raised when the data provider is unavailable."""
    pass


class NoDataError(SignalAnalysisError):
    """Raised when no data is available for the symbol."""
    pass


class ThinHistoryError(SignalAnalysisError):
    """Raised when there is not enough price history."""
    def __init__(self, symbol: str, available: int, needed: int):
        self.symbol = symbol
        self.available = available
        self.needed = needed
        super().__init__(f"Not enough price history for {symbol} to compute signals: only {available} trading day(s) available, need at least {needed}. The symbol may have been listed too recently — check back once it has more trading history.")


class SignalResult(TypedDict):
    symbol: str
    period: str
    signal: str
    score: float
    confidence: float
    reasons: list[str]
    price: float
    timestamp: str | None
    indicators: dict
    volume_spike: bool
    breakout: bool


MIN_HISTORY_BARS = 20


def _df_col(df, col, n):
    """Extract a column from DataFrame, or return [None]*n if unavailable."""
    if df is None or not hasattr(df, "columns") or col not in df.columns:
        return [None] * n
    return df[col].tolist()


def signal_from_score(score: float) -> str:
    """Map numeric score to signal string."""
    if score >= 0.75:
        return "BUY"
    if score <= -0.75:
        return "SELL"
    return "NEUTRAL"


def signal_to_numeric(signal: str) -> int:
    """Map signal string to numeric value: BUY=1, NEUTRAL=0, SELL=-1."""
    if signal == "BUY":
        return 1
    if signal == "SELL":
        return -1
    return 0


def compute_indicators(
    close, high, low, volume, n,
    macd_df=None,
) -> dict:
    """Compute all indicator values from OHLCV data."""
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

    macd_hist_list = _df_col(macd_df, "MACDh_12_26_9", n)
    macd_hist = (
        _clean(macd_hist_list[-1])
        if macd_hist_list and not isinstance(macd_hist_list[0], type(None))
        else None
    )

    vol_avg = volume.rolling(20).mean()
    vol_ratio = (
        _clean(float(volume.iloc[-1] / vol_avg.iloc[-1]))
        if not math.isnan(vol_avg.iloc[-1])
        else None
    )

    rsi_vals = ta.rsi(close_series, length=14)
    latest_rsi = _clean(float(rsi_vals.iloc[-1])) if not rsi_vals.empty else None

    sma50_val = ta.sma(close_series, length=50)
    latest_sma50 = (
        _clean(float(sma50_val.iloc[-1])) if len(close_series) >= 50 and not math.isnan(sma50_val.iloc[-1]) else None
    )

    return {
        "bias": bias,
        "kdj_k": kdj_k,
        "kdj_d": kdj_d,
        "macd_histogram": macd_hist,
        "volume_ratio": vol_ratio,
        "rvol": vol_ratio,
        "rsi": latest_rsi,
        "sma20": _clean(latest_sma20),
        "sma50": latest_sma50,
    }


def compute_52w_metrics(close_price: float, high_52w: float | None, low_52w: float | None) -> dict:
    """Compute 52-week metrics from price data."""
    if high_52w is None or low_52w is None:
        return {
            "high_52w": None,
            "low_52w": None,
            "pct_from_52w_high": None,
        }
    pct_from_high = _clean((close_price - high_52w) / high_52w * 100) if high_52w else None
    return {
        "high_52w": _clean(high_52w),
        "low_52w": _clean(low_52w),
        "pct_from_52w_high": pct_from_high,
    }


def is_breakout(close_price: float, high_52w: float | None, rvol: float | None) -> bool:
    """Determine if current price is in breakout condition.

    Breakout = latest close is within 2% of 52-week high AND rvol > 1.5.
    """
    if high_52w is None or rvol is None:
        return False
    return close_price >= 0.98 * high_52w and rvol > 1.5


def score_signals(
    bias: float | None,
    macd_hist: float | None,
    kdj_k: float | None,
    kdj_d: float | None,
    vol_ratio: float | None,
    rvol: float | None,
    breakout: bool,
    high_52w: float | None,
    close_price: float | None = None,
) -> tuple[float, list[str]]:
    """Compute signal score and reasons from indicator values.

    Returns (score, reasons).
    """
    reasons = []
    score = 0.0

    if bias is not None and bias < -3:
        score += 0.25
        reasons.append(f"BIAS={bias:.1f} (< -3, oversold)")
    elif bias is not None and bias > 3:
        score -= 0.25
        reasons.append(f"BIAS={bias:.1f} (> +3, overbought)")

    if macd_hist is not None and macd_hist > 0:
        score += 0.25
        reasons.append(f"MACD hist positive ({macd_hist:.4f})")
    elif macd_hist is not None and macd_hist < 0:
        score -= 0.25
        reasons.append(f"MACD hist negative ({macd_hist:.4f})")

    if kdj_k is not None and kdj_d is not None:
        if kdj_k > kdj_d:
            score += 0.25
            reasons.append(f"KDJ golden cross (K={kdj_k:.1f} > D={kdj_d:.1f})")
        else:
            score -= 0.25
            reasons.append(f"KDJ death cross (K={kdj_k:.1f} < D={kdj_d:.1f})")

    if vol_ratio is not None and vol_ratio > 1.2:
        if score > 0:
            score += 0.25
            if rvol is not None and rvol > 2.0:
                reasons.append(f"Unusual volume ({vol_ratio:.2f}x avg, {rvol:.1f}x rvol)")
            else:
                reasons.append(f"Volume surge ({vol_ratio:.2f}x avg)")
        elif score < 0:
            score -= 0.25
            if rvol is not None and rvol > 2.0:
                reasons.append(f"High volume selling ({vol_ratio:.2f}x avg, {rvol:.1f}x rvol)")
            else:
                reasons.append(f"High volume selling ({vol_ratio:.2f}x avg)")

    if breakout and high_52w is not None:
        score += 0.25
        reasons.append("52-week breakout on volume")

    if (
        not breakout
        and high_52w is not None
        and close_price is not None
        and close_price >= 0.98 * high_52w
    ):
        reasons.append("Near 52-week high (no volume confirmation)")

    return score, reasons


def build_signal_result(
    symbol: str,
    period: str,
    latest_close: float,
    timestamp: str | None,
    indicators: dict,
    score: float,
    reasons: list[str],
    volume_spike: bool,
    breakout: bool,
    high_52w: float | None,
    low_52w: float | None,
) -> SignalResult:
    """Build the final signal result dict."""
    signal = signal_from_score(score)
    confidence = min(abs(score), 1.0)

    result_indicators = dict(indicators)
    result_indicators.update(compute_52w_metrics(latest_close, high_52w, low_52w))

    return {
        "symbol": symbol.upper(),
        "period": period,
        "signal": signal,
        "score": round(score, 2),
        "confidence": round(confidence, 2),
        "reasons": reasons,
        "price": round(latest_close, 2),
        "timestamp": timestamp,
        "indicators": result_indicators,
        "volume_spike": volume_spike,
        "breakout": breakout,
    }


async def compute_analysis_impl(symbol: str, period: str = "3mo", provider=None) -> SignalResult:
    """Core signal computation shared by routes and cron scan.

    Args:
        symbol: Stock symbol
        period: Time period (1d, 5d, 1mo, 3mo, etc.)
        provider: Market data provider (defaults to module-level market_provider)

    Raises:
        ProviderUnavailableError: when the data provider is unavailable
        NoDataError: when no data is returned for the symbol
        ThinHistoryError: when there's not enough price history
    """
    if provider is None:
        provider = market_provider
    interval_map = {"1d": "5m", "5d": "15m"}
    interval = interval_map.get(period, "1d")

    try:
        result = await provider.get_history(
            symbol.upper(), period=period, interval=interval
        )
    except RuntimeError as exc:
        raise ProviderUnavailableError(f"Data provider unavailable for {symbol}") from exc

    df = result.value

    if df.empty:
        raise NoDataError(f"No data for {symbol}")

    if len(df) < MIN_HISTORY_BARS:
        raise ThinHistoryError(symbol, len(df), MIN_HISTORY_BARS)

    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]
    n = len(close)
    latest_close = float(close.iloc[-1])

    try:
        macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    except Exception:
        macd_df = None

    indicators = compute_indicators(close, high, low, volume, n, macd_df)
    rvol = indicators.get("rvol")
    volume_spike = rvol is not None and rvol > 2.0

    high_52w = None
    low_52w = None
    breakout = False

    try:
        result_1y = await provider.get_history(
            symbol.upper(), period="1y", interval="1d"
        )
        df_1y = result_1y.value
        if not df_1y.empty:
            high_52w = float(df_1y["High"].max())
            low_52w = float(df_1y["Low"].min())
            breakout = is_breakout(latest_close, high_52w, rvol)
    except Exception:
        pass

    score, reasons = score_signals(
        bias=indicators.get("bias"),
        macd_hist=indicators.get("macd_histogram"),
        kdj_k=indicators.get("kdj_k"),
        kdj_d=indicators.get("kdj_d"),
        vol_ratio=indicators.get("volume_ratio"),
        rvol=rvol,
        breakout=breakout,
        high_52w=high_52w,
        close_price=latest_close,
    )

    return build_signal_result(
        symbol=symbol,
        period=period,
        latest_close=latest_close,
        timestamp=df.index[-1].isoformat() if len(df) > 0 else None,
        indicators=indicators,
        score=score,
        reasons=reasons,
        volume_spike=volume_spike,
        breakout=breakout,
        high_52w=high_52w,
        low_52w=low_52w,
    )