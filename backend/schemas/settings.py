"""
schemas/settings.py — Pydantic schemas for settings endpoints.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional


class SettingsRead(BaseModel):
    trading_mode: str
    capital: float
    risk_pct: float
    max_sl_pct: float
    max_trades_per_day: int
    vol_mult: float
    expansion_pct: float
    rsi_oversold: int
    min_quality: int
    groww_api_configured: bool
    telegram_configured: bool


class SettingsUpdate(BaseModel):
    trading_mode: Optional[Literal["paper", "forward", "live"]] = None
    capital: Optional[float] = Field(default=None, ge=10000)
    risk_pct: Optional[float] = Field(default=None, ge=0.5, le=5.0)
    max_sl_pct: Optional[float] = Field(default=None, ge=1.0, le=20.0)
    max_trades_per_day: Optional[int] = Field(default=None, ge=1, le=10)
    vol_mult: Optional[float] = None
    expansion_pct: Optional[float] = None
    rsi_oversold: Optional[int] = None
    min_quality: Optional[int] = Field(default=None, ge=0, le=100)
    groww_api_key: Optional[str] = None
    groww_secret_key: Optional[str] = None
    groww_client_id: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None


class LiveModeRequest(BaseModel):
    """Extra confirmation required to switch to live trading."""
    confirm: bool = Field(..., description="Must be True to enable live mode")
    groww_api_key: str
    groww_secret_key: str
    groww_client_id: str
