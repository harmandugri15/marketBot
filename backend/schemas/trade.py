"""
schemas/trade.py — Pydantic schemas for trade endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Literal


class TradeCreate(BaseModel):
    symbol: str
    strategy: str = "VCP"
    entry_price: float
    quantity: int = Field(ge=1)
    stop_loss: float
    target: Optional[float] = None
    capital_deployed: Optional[float] = None


class TradeClose(BaseModel):
    exit_price: float
    exit_reason: Literal["SL_HIT", "TARGET_HIT", "MANUAL", "TRAILING"] = "MANUAL"


class TradeRead(BaseModel):
    id: int
    symbol: str
    strategy: str
    mode: str
    status: str
    entry_price: float
    entry_date: datetime
    quantity: int
    stop_loss: float
    target: Optional[float]
    exit_price: Optional[float]
    exit_date: Optional[datetime]
    exit_reason: Optional[str]
    pnl: Optional[float]
    pnl_pct: Optional[float]
    capital_deployed: Optional[float]
    groww_order_id: Optional[str]

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    open_trades: int
    total_trades: int
    open_pnl: float
    realized_pnl: float
    win_rate: float
    trading_mode: str
