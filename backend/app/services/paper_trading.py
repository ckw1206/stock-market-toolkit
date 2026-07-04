"""Paper-trading portfolio service — simulated buys/sells at real quotes.

Lets a user validate the toolkit's signals risk-free before committing real
capital: "buy"/"sell" at the latest close, track open positions and P&L.

Position accounting uses a weighted-average-cost method (not FIFO lots):
avg_cost is the qty-weighted average of buy fills; sells reduce quantity but
leave avg_cost unchanged. That's a simplification appropriate for a paper
portfolio, not brokerage-grade tax-lot accounting.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaperPortfolio, PaperTrade
from app.providers import market_provider

VALID_SIDES = ("buy", "sell")


class PaperTradingError(Exception):
    """Base class for paper-trading errors."""


class InvalidSideError(PaperTradingError):
    pass


class InvalidQuantityError(PaperTradingError):
    pass


class InsufficientCashError(PaperTradingError):
    pass


class InsufficientSharesError(PaperTradingError):
    pass


class QuoteUnavailableError(PaperTradingError):
    pass


async def get_or_create_portfolio(db: AsyncSession, user_id: str) -> PaperPortfolio:
    """Get the user's paper portfolio, creating it on first use.

    The Dashboard/Portfolio page fires GET /portfolio and GET /history
    concurrently, so two requests can both see "no portfolio yet" and race
    to insert one. Since user_id is unique, the loser's INSERT raises
    IntegrityError — recover by rolling back and re-reading the winner's row
    instead of surfacing a 500.
    """
    result = await db.execute(select(PaperPortfolio).where(PaperPortfolio.user_id == user_id))
    portfolio = result.scalar_one_or_none()
    if portfolio is not None:
        return portfolio

    portfolio = PaperPortfolio(user_id=user_id)
    db.add(portfolio)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        result = await db.execute(select(PaperPortfolio).where(PaperPortfolio.user_id == user_id))
        portfolio = result.scalar_one_or_none()
        if portfolio is None:
            raise
        return portfolio

    await db.refresh(portfolio)
    return portfolio


async def get_latest_price(symbol: str) -> float:
    try:
        result = await market_provider.get_history(symbol.upper(), period="5d", interval="1d")
    except RuntimeError as exc:
        raise QuoteUnavailableError(f"Data provider unavailable for {symbol}") from exc
    df = result.value
    if df.empty:
        raise QuoteUnavailableError(f"No price data for {symbol}")
    return float(df["Close"].iloc[-1])


def _held_qty(trades: list[PaperTrade], symbol: str) -> float:
    qty = 0.0
    for t in trades:
        if t.symbol != symbol:
            continue
        qty += t.qty if t.side == "buy" else -t.qty
    return qty


async def execute_trade(db: AsyncSession, user_id: str, symbol: str, side: str, qty: float) -> dict:
    """Execute a simulated buy/sell at the latest close for `symbol`.

    Raises:
        InvalidSideError, InvalidQuantityError, QuoteUnavailableError,
        InsufficientCashError, InsufficientSharesError
    """
    side = side.lower()
    if side not in VALID_SIDES:
        raise InvalidSideError(f"side must be 'buy' or 'sell', got {side!r}")
    if qty <= 0:
        raise InvalidQuantityError("qty must be positive")

    symbol = symbol.upper()
    portfolio = await get_or_create_portfolio(db, user_id)
    price = await get_latest_price(symbol)
    cost = qty * price

    if side == "buy":
        if cost > portfolio.cash:
            raise InsufficientCashError(f"Insufficient cash: need {cost:.2f}, have {portfolio.cash:.2f}")
        portfolio.cash -= cost
    else:
        existing = await db.execute(
            select(PaperTrade).where(PaperTrade.portfolio_id == portfolio.id)
        )
        held = _held_qty(list(existing.scalars().all()), symbol)
        if qty > held:
            raise InsufficientSharesError(f"Insufficient shares: trying to sell {qty}, hold {held}")
        portfolio.cash += cost

    trade = PaperTrade(portfolio=portfolio, symbol=symbol, side=side, qty=qty, price=price)
    db.add(trade)
    await db.commit()

    return {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": round(price, 2),
        "cash_after": round(portfolio.cash, 2),
    }


async def get_portfolio_view(db: AsyncSession, user_id: str) -> dict:
    """Aggregate trade history into open positions, mark-to-market with latest quotes."""
    portfolio = await get_or_create_portfolio(db, user_id)

    result = await db.execute(
        select(PaperTrade)
        .where(PaperTrade.portfolio_id == portfolio.id)
        .order_by(PaperTrade.executed_at)
    )
    trades = list(result.scalars().all())

    by_symbol: dict[str, dict] = {}
    for t in trades:
        pos = by_symbol.setdefault(t.symbol, {"qty": 0.0, "buy_qty": 0.0, "buy_cost": 0.0})
        if t.side == "buy":
            pos["qty"] += t.qty
            pos["buy_qty"] += t.qty
            pos["buy_cost"] += t.qty * t.price
        else:
            pos["qty"] -= t.qty

    positions = []
    total_unrealized_pnl = 0.0
    market_value_total = 0.0

    for symbol, pos in sorted(by_symbol.items()):
        if pos["qty"] <= 0:
            continue
        avg_cost = pos["buy_cost"] / pos["buy_qty"] if pos["buy_qty"] > 0 else 0.0
        try:
            last_price = await get_latest_price(symbol)
        except QuoteUnavailableError:
            last_price = None

        market_value = pos["qty"] * last_price if last_price is not None else None
        unrealized_pnl = (last_price - avg_cost) * pos["qty"] if last_price is not None else None
        unrealized_pnl_pct = (
            round((last_price - avg_cost) / avg_cost * 100, 2)
            if last_price is not None and avg_cost > 0
            else None
        )

        if unrealized_pnl is not None:
            total_unrealized_pnl += unrealized_pnl
        if market_value is not None:
            market_value_total += market_value

        positions.append(
            {
                "symbol": symbol,
                "qty": pos["qty"],
                "avg_cost": round(avg_cost, 2),
                "last_price": round(last_price, 2) if last_price is not None else None,
                "market_value": round(market_value, 2) if market_value is not None else None,
                "unrealized_pnl": round(unrealized_pnl, 2) if unrealized_pnl is not None else None,
                "unrealized_pnl_pct": unrealized_pnl_pct,
            }
        )

    return {
        "cash": round(portfolio.cash, 2),
        "positions": positions,
        "equity": round(portfolio.cash + market_value_total, 2),
        "total_unrealized_pnl": round(total_unrealized_pnl, 2),
    }


async def get_trade_history(db: AsyncSession, user_id: str, limit: int = 100) -> list[dict]:
    portfolio = await get_or_create_portfolio(db, user_id)
    result = await db.execute(
        select(PaperTrade)
        .where(PaperTrade.portfolio_id == portfolio.id)
        .order_by(PaperTrade.executed_at.desc(), PaperTrade.id.desc())
        .limit(limit)
    )
    trades = result.scalars().all()
    return [
        {
            "id": t.id,
            "symbol": t.symbol,
            "side": t.side,
            "qty": t.qty,
            "price": t.price,
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
        }
        for t in trades
    ]
