"""Paper-trading portfolio service — simulated buys/sells at real quotes.

Lets a user validate the toolkit's signals risk-free before committing real
capital: "buy"/"sell" at the latest close, track open positions and P&L.

Position accounting uses a weighted-average-cost method (not FIFO lots):
avg_cost is the qty-weighted average of buy fills; sells reduce quantity but
leave avg_cost unchanged. That's a simplification appropriate for a paper
portfolio, not brokerage-grade tax-lot accounting.
"""

from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaperPortfolio, PaperTrade
from app.models.paper import DEFAULT_STARTING_CASH
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


async def get_or_create_portfolio(
    db: AsyncSession, user_id: str, starting_cash: float | None = None
) -> PaperPortfolio:
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

    initial_cash = starting_cash if starting_cash is not None else DEFAULT_STARTING_CASH
    portfolio = PaperPortfolio(user_id=user_id, cash=initial_cash, starting_cash=initial_cash)
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


# Shortest period whose window covers a given lookback, so a backdated trade
# fetches enough history to reach its date without pulling "max" every time.
_PERIOD_SPANS = (("1mo", 31), ("3mo", 93), ("6mo", 186), ("1y", 372), ("2y", 744), ("5y", 1860))


async def get_price_asof(symbol: str, when: datetime) -> float:
    """Close on the last trading day on or before ``when``.

    Backdated trades must be priced at their historical close, not the latest
    one — otherwise avg_cost equals the current price and unrealized P&L is
    always ~0. Falls back to the earliest available close if history doesn't
    reach back to ``when``.
    """
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    days_back = max((datetime.now(timezone.utc) - when).days, 0) + 5
    period = next((p for p, span in _PERIOD_SPANS if days_back <= span), "max")
    try:
        result = await market_provider.get_history(symbol.upper(), period=period, interval="1d")
    except RuntimeError as exc:
        raise QuoteUnavailableError(f"Data provider unavailable for {symbol}") from exc
    df = result.value
    if df.empty:
        raise QuoteUnavailableError(f"No price data for {symbol}")
    on_or_before = df[df.index.date <= when.date()]
    if not on_or_before.empty:
        return float(on_or_before["Close"].iloc[-1])
    return float(df["Close"].iloc[0])


def _held_qty(trades: list[PaperTrade], symbol: str) -> float:
    qty = 0.0
    for t in trades:
        if t.symbol != symbol:
            continue
        qty += t.qty if t.side == "buy" else -t.qty
    return qty


async def execute_trade(
    db: AsyncSession, user_id: str, symbol: str, side: str, qty: float, executed_at: datetime | None = None
) -> dict:
    """Execute a simulated buy/sell at the latest close for `symbol`.

    Args:
        executed_at: Optional backdated timestamp for the trade. Must not be in the future.
            Defaults to datetime.utcnow().

    Raises:
        InvalidSideError, InvalidQuantityError, QuoteUnavailableError,
        InsufficientCashError, InsufficientSharesError
    """
    side = side.lower()
    if side not in VALID_SIDES:
        raise InvalidSideError(f"side must be 'buy' or 'sell', got {side!r}")
    if qty <= 0:
        raise InvalidQuantityError("qty must be positive")

    backdated = executed_at is not None
    if executed_at is None:
        executed_at = datetime.now(timezone.utc)

    symbol = symbol.upper()
    portfolio = await get_or_create_portfolio(db, user_id)
    # Backdated trades price at the historical close on their date, not today's.
    price = await get_price_asof(symbol, executed_at) if backdated else await get_latest_price(symbol)
    cost = qty * price

    if side == "buy":
        if cost > portfolio.cash:
            raise InsufficientCashError(f"Insufficient cash: need {cost:.2f}, have {portfolio.cash:.2f}")
        portfolio.cash = float(portfolio.cash) - cost
    else:
        existing = await db.execute(
            select(PaperTrade).where(PaperTrade.portfolio_id == portfolio.id)
        )
        held = _held_qty(list(existing.scalars().all()), symbol)
        if qty > held:
            raise InsufficientSharesError(f"Insufficient shares: trying to sell {qty}, hold {held}")
        portfolio.cash = float(portfolio.cash) + cost

    trade = PaperTrade(portfolio=portfolio, symbol=symbol, side=side, qty=qty, price=price, executed_at=executed_at)
    db.add(trade)
    await db.commit()

    return {
        "symbol": symbol,
        "side": side,
        "qty": qty,
        "price": round(price, 2),
        "cash_after": round(float(portfolio.cash), 2),
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

    cash_val = float(portfolio.cash)
    return {
        "cash": round(cash_val, 2),
        "starting_cash": round(float(portfolio.starting_cash), 2),
        "positions": positions,
        "equity": round(cash_val + market_value_total, 2),
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


async def undo_trade(db: AsyncSession, user_id: str, trade_id: int) -> dict:
    """Delete a trade by ID and recompute portfolio cash and positions from the remaining history.

    Raises:
        ValueError: trade not found or does not belong to the calling user.
    """
    portfolio = await get_or_create_portfolio(db, user_id)

    result = await db.execute(
        select(PaperTrade).where(
            PaperTrade.id == trade_id, PaperTrade.portfolio_id == portfolio.id
        )
    )
    trade = result.scalar_one_or_none()
    if trade is None:
        raise ValueError(f"Trade {trade_id} not found for this user")

    # Recompute cash from all OTHER trades (excluding this one), using the same
    # derivation logic that get_portfolio_view relies on, to avoid drift.
    all_trades_result = await db.execute(
        select(PaperTrade)
        .where(PaperTrade.portfolio_id == portfolio.id, PaperTrade.id != trade_id)
        .order_by(PaperTrade.executed_at)
    )
    remaining_trades = list(all_trades_result.scalars().all())

    # Recompute cash
    cash = float(portfolio.starting_cash)
    for t in remaining_trades:
        cost = t.qty * t.price
        if t.side == "buy":
            cash -= cost
        else:
            cash += cost

    portfolio.cash = cash
    await db.flush()
    await db.delete(trade)
    await db.commit()

    return await get_portfolio_view(db, user_id)


async def reset_portfolio(
    db: AsyncSession, user_id: str, starting_cash: float | None = None
) -> dict:
    """Delete all trades and reset cash to starting_cash.

    When ``starting_cash`` is provided it also updates the stored starting
    balance — the only way to reconfigure it after creation, since the
    portfolio is auto-created (with the default) on first view.

    Returns the reset portfolio view.
    """
    portfolio = await get_or_create_portfolio(db, user_id)

    if starting_cash is not None:
        portfolio.starting_cash = starting_cash

    # Reset cash to starting_cash
    portfolio.cash = float(portfolio.starting_cash)
    await db.flush()

    # Delete all trades for this portfolio
    await db.execute(
        delete(PaperTrade).where(PaperTrade.portfolio_id == portfolio.id)
    )

    await db.commit()

    return await get_portfolio_view(db, user_id)
