import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from app.models import User
from app.schemas import (
    StockInfoResponse,
    FundamentalsResponse,
    ProfitabilityMetrics,
    DividendQualityDetails,
    DividendsResponse,
    YearlyDividend,
)
from app.auth import get_current_user
from app.providers import market_provider, fundamentals_provider
from app.services.scoring import (
    piotroski_f_score,
    profitability_metrics,
    dividend_quality,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["stock-info"])


@router.get("/stock/{symbol}/info", response_model=StockInfoResponse)
async def get_stock_info(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    try:
        result = await market_provider.get_info(symbol.upper())
    except Exception as exc:
        log.error("Failed to get stock info for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Stock info service temporarily unavailable. Please try again later."
        )
    info = result.value

    return StockInfoResponse(
        symbol=symbol.upper(),
        cached_at=datetime.utcnow().isoformat(),
        source=result.source,
        as_of=result.as_of,
        short_name=info.get("shortName", symbol.upper()),
        long_name=info.get("longName"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        price=info.get("currentPrice") or info.get("regularMarketPrice", 0),
        previous_close=info.get("regularMarketPreviousClose") or info.get("previousClose"),
        currency=info.get("currency"),
        market_cap=info.get("marketCap"),
        sharesOutstanding=info.get("sharesOutstanding"),
        trailing_pe=info.get("trailingPE"),
        forward_pe=info.get("forwardPE"),
        dividend_yield=info.get("dividendYield"),
        avg_volume=info.get("averageVolume"),
        beta=info.get("beta"),
        week_52_high=info.get("fiftyTwoWeekHigh"),
        week_52_low=info.get("fiftyTwoWeekLow"),
    )


@router.get("/stock/{symbol}/fundamentals", response_model=FundamentalsResponse)
async def get_fundamentals(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    try:
        data = await fundamentals_provider.get_fundamentals_dict(symbol.upper())
    except Exception as exc:
        log.error("Failed to get fundamentals for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Fundamentals service temporarily unavailable."
        )
    cur = data.get("current", {})
    prev = data.get("prior", {})

    if not cur or not prev:
        raise HTTPException(
            status_code=404, detail=f"No fundamentals data for {symbol}"
        )

    f_score = piotroski_f_score(cur, prev)
    p_metrics = profitability_metrics(cur, prev)
    try:
        div_df = await fundamentals_provider.get_dividends(symbol.upper())
    except Exception as exc:
        log.error("Failed to get dividends for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Fundamentals service temporarily unavailable."
        )
    dq = dividend_quality(cur, prev, div_df)

    return FundamentalsResponse(
        symbol=symbol.upper(),
        cached_at=datetime.utcnow().isoformat(),
        f_score=f_score,
        profitability=ProfitabilityMetrics(**p_metrics),
        dividend_quality=DividendQualityDetails(score=dq["score"], **dq["details"]),
        statements={"current": cur, "prior": prev},
    )


@router.get("/stock/{symbol}/dividends", response_model=DividendsResponse)
async def get_dividends(
    symbol: str,
    current_user: User = Depends(get_current_user),
):
    try:
        divs = await fundamentals_provider.get_dividends(symbol.upper())
    except Exception as exc:
        log.error("Failed to get dividends for %s: %s", symbol, exc, exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Fundamentals service temporarily unavailable."
        )

    if divs.empty:
        return DividendsResponse(
            symbol=symbol.upper(),
            cached_at=datetime.utcnow().isoformat(),
            yearly=[],
            streak=0,
        )

    # Yearly totals
    yearly_totals = divs.groupby(divs.index.year).sum()
    yearly = [
        YearlyDividend(year=int(year), total=round(float(total), 4))
        for year, total in yearly_totals.items()
    ]
    yearly.sort(key=lambda y: y.year)

    # Consecutive streak (from latest year backwards)
    streak = 0
    if yearly:
        all_years = sorted(set(divs.index.year))
        latest = all_years[-1]
        y = latest
        while y in all_years:
            streak += 1
            y -= 1

    # Yield & payout ratio (using most recent year's total)
    latest_total = yearly[-1].total if yearly else 0
    yield_pct = None
    payout_ratio = None
    try:
        info = (await market_provider.get_info(symbol.upper())).value
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price and latest_total:
            yield_pct = round(latest_total / price * 100, 2)
        eps = info.get("trailingEps")
        if eps and latest_total:
            payout_ratio = round(latest_total / eps * 100, 2)
    except Exception:
        pass

    return DividendsResponse(
        symbol=symbol.upper(),
        cached_at=datetime.utcnow().isoformat(),
        yearly=yearly,
        yield_pct=yield_pct,
        payout_ratio=payout_ratio,
        streak=streak,
    )
