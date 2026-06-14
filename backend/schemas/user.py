from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=6)


class UserRead(BaseModel):
    id: int
    username: str
    trading_mode: str
    capital: float
    risk_pct: float
    max_sl_pct: float
    min_quality: int
    created_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    trading_mode: Optional[str] = None
    capital: Optional[float] = None
    risk_pct: Optional[float] = None
    max_sl_pct: Optional[float] = None
    min_quality: Optional[int] = None
    groww_api_key: Optional[str] = None
    groww_secret_key: Optional[str] = None
    groww_client_id: Optional[str] = None
