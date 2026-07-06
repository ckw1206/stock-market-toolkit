from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from app.database import Base

DEFAULT_STARTING_CASH = 100_000.0


class PaperPortfolio(Base):
    __tablename__ = "paper_portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False, unique=True)
    cash: Mapped[float] = mapped_column(Numeric, nullable=False, default=DEFAULT_STARTING_CASH)
    starting_cash: Mapped[float] = mapped_column(Numeric, nullable=False, default=DEFAULT_STARTING_CASH)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    trades = relationship(
        "PaperTrade", back_populates="portfolio", cascade="all, delete-orphan"
    )


class PaperTrade(Base):
    __tablename__ = "paper_trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    portfolio_id = Column(
        Integer, ForeignKey("paper_portfolios.id", ondelete="CASCADE"), nullable=False
    )
    symbol = Column(String, nullable=False, index=True)
    side = Column(String, nullable=False)  # buy | sell
    qty = Column(Float, nullable=False)
    price = Column(Float, nullable=False)  # fill price at execution
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    portfolio = relationship("PaperPortfolio", back_populates="trades")
