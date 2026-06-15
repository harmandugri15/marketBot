from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional


class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8)

    @field_validator("password")
    @classmethod
    def password_must_contain_letter_and_digit(cls, v: str) -> str:
        if not any(c.isalpha() for c in v) or not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one letter and one digit")
        return v


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
