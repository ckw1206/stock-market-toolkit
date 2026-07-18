"""Holdings ledger: real brokerage transactions (pure ledger, compute-on-read).

qty/price/amount/fee are stored as strings: SQLite has no native DECIMAL and
SQLAlchemy Numeric round-trips through float there. The ledger service
converts to Decimal at the boundary.
"""
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class PortfolioTransaction(Base):
    __tablename__ = "portfolio_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String, nullable=False)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    qty: Mapped[str | None] = mapped_column(String, nullable=True)
    price: Mapped[str | None] = mapped_column(String, nullable=True)
    amount: Mapped[str | None] = mapped_column(String, nullable=True)
    fee: Mapped[str] = mapped_column(String, nullable=False, default="0", server_default="0")
    currency: Mapped[str] = mapped_column(String, nullable=False)
    note: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class PortfolioSuggestionDismissal(Base):
    __tablename__ = "portfolio_suggestion_dismissals"
    __table_args__ = (
        UniqueConstraint("user_id", "symbol", "type", "ex_date",
                         name="uq_portfolio_dismissal"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id"), nullable=False, index=True
    )
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    ex_date: Mapped[date] = mapped_column(Date, nullable=False)
