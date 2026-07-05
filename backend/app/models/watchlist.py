from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, JSON
from sqlalchemy.sql import func
from app.database import Base


class Watchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    symbol = Column(String, nullable=False)
    note = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)  # list[str], lowercase (e.g. ["swing", "earnings-play"])
    created_at = Column(DateTime(timezone=True), server_default=func.now())
