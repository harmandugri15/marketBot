"""
models/backtest_result.py
-------------------------
Stores each complete backtest run with aggregated stats and trade log.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from database import Base


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id           = Column(Integer, primary_key=True, index=True)
    run_date     = Column(DateTime(timezone=True), server_default=func.now())
    strategy     = Column(String(20), default="VCP")

    # Date range tested
    start_date   = Column(String(10))
    end_date     = Column(String(10))

    # Capital
    initial_capital = Column(Float)
    final_capital   = Column(Float)
    max_drawdown    = Column(Float)

    # Performance
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate     = Column(Float)   # 0–100
    avg_gain_pct = Column(Float)
    avg_loss_pct = Column(Float)
    profit_factor = Column(Float)
    sharpe_ratio  = Column(Float, nullable=True)
    total_return_pct = Column(Float)

    # Full trade log (list of dicts) and equity curve stored as JSON
    trade_log    = Column(JSON, default=list)
    equity_curve = Column(JSON, default=list)

    notes        = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Backtest {self.strategy} {self.start_date}→{self.end_date} wr={self.win_rate}%>"
