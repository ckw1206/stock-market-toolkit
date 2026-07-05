from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class WatchlistCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)


class WatchlistUpdate(BaseModel):
    note: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[list[str]] = Field(default=None, max_length=20)


class WatchlistResponse(BaseModel):
    id: int
    user_id: str
    symbol: str
    note: Optional[str] = None
    tags: list[str] = []
    created_at: Optional[datetime] = None

    @field_validator("tags", mode="before")
    @classmethod
    def _default_tags(cls, v):
        return v or []

    class Config:
        from_attributes = True
