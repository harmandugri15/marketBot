"""
schemas/signal.py — Pydantic schemas for signal API responses.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SignalBase(BaseModel):
    symbol: str
    strategy: str = "VCP"
    close: float
    entry: float
    stop_loss: float
    target: Optional[float] = None
    quality: int = Field(ge=0, le=100)
    rsi: Optional[float] = None
    vol_ratio: Optional[float] = None
    pullback_pct: Optional[float] = None
    market_regime: Optional[str] = None
    notes: Optional[str] = None


class SignalCreate(SignalBase):
    pass


class SignalRead(SignalBase):
    id: int
    scan_date: datetime
    is_active: bool

    model_config = {"from_attributes": True}


class SignalListResponse(BaseModel):
    count: int
    market_regime: Optional[str] = None
    signals: list[SignalRead]
