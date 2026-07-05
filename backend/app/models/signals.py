from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class SignalScan(Base):
    __tablename__ = "signal_scans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_run_id = Column(Integer, ForeignKey("job_runs.id", ondelete="SET NULL"), nullable=True)
    scanned_at = Column(DateTime(timezone=True), server_default=func.now())

    results = relationship("ScanResult", back_populates="scan", cascade="all, delete-orphan")


class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scan_id = Column(Integer, ForeignKey("signal_scans.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String, nullable=False, index=True)
    signal = Column(String, nullable=False)
    score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    price = Column(Float, nullable=True)
    rvol = Column(Float, nullable=True)
    breakout = Column(Boolean, default=False)
    volume_spike = Column(Boolean, default=False)
    reasons = Column(JSON, nullable=True)
    rank = Column(Integer, nullable=True)
    # Screener enrichment (populated at scan time)
    rsi = Column(Float, nullable=True)
    sma20 = Column(Float, nullable=True)
    sma50 = Column(Float, nullable=True)
    sma200 = Column(Float, nullable=True)
    prev_close = Column(Float, nullable=True)
    volume_ratio = Column(Float, nullable=True)
    pct_from_52w_high = Column(Float, nullable=True)
    pct_change_1d = Column(Float, nullable=True)
    sector = Column(String, nullable=True)

    scan = relationship("SignalScan", back_populates="results")


class MarketBreadth(Base):
    """One row per trading day: aggregate market-wide breadth stats."""

    __tablename__ = "market_breadth"

    # date is the primary key; the scan that produced this breadth row is
    # recorded via scan_id so we can join for scanned_at ordering.
    date = Column(Date, primary_key=True)
    scan_id = Column(Integer, ForeignKey("signal_scans.id", ondelete="CASCADE"), nullable=False)
    pct_above_50dma = Column(Float, nullable=True)
    pct_above_200dma = Column(Float, nullable=True)
    advancers = Column(Integer, nullable=False, default=0)
    decliners = Column(Integer, nullable=False, default=0)
    new_highs = Column(Integer, nullable=False, default=0)
    new_lows = Column(Integer, nullable=False, default=0)
    computed_at = Column(DateTime(timezone=True), server_default=func.now())

    scan = relationship("SignalScan")