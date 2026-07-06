from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PaperTradeRequest(BaseModel):
    model_config = ConfigDict(ser_json_timedelta="iso8601")
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(buy|sell)$")
    qty: float = Field(..., gt=0)
    executed_at: datetime | None = Field(
        None,
        description="Optional backdated timestamp (ISO-8601). Must not be in the future.",
    )


class PaperPortfolioCreate(BaseModel):
    starting_cash: float = Field(100_000.0, gt=0, description="Initial cash balance for the portfolio.")
