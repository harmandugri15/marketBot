"""
schemas/backtest.py — Pydantic schemas for backtest endpoints.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class BacktestRequest(BaseModel):
    strategy: str = "VCP"
    start_date: str = "2024-01-01"
    end_date: str = "2024-12-31"
    capital: float = Field(default=200000.0, ge=10000)
    universe: str = "ALL"
    symbols: Optional[list[str]] = None   # None = use resolved universe


class BacktestSummary(BaseModel):
    id: int
    run_date: datetime
    strategy: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    win_rate: float
    total_trades: int
    max_drawdown: float
    profit_factor: float

    model_config = {"from_attributes": True}


class BacktestDetail(BacktestSummary):
    trade_log: list
    equity_curve: list
    winning_trades: int
    losing_trades: int
    avg_gain_pct: float
    avg_loss_pct: float
    sharpe_ratio: Optional[float]


class BacktestProgress(BaseModel):
    running: bool
    current: int
    total: int
    symbol: str
    done: bool
    error: Optional[str]
