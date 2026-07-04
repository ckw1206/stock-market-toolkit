from pydantic import BaseModel, Field


class PaperTradeRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    side: str = Field(..., pattern="^(buy|sell)$")
    qty: float = Field(..., gt=0)
