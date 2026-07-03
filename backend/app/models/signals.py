from sqlalchemy import Column, Integer, String, Float, Boolean, JSON, DateTime, ForeignKey
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
    volume_ratio = Column(Float, nullable=True)
    pct_from_52w_high = Column(Float, nullable=True)
    pct_change_1d = Column(Float, nullable=True)
    sector = Column(String, nullable=True)

    scan = relationship("SignalScan", back_populates="results")