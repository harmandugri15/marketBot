"""
models/forward_test_log.py
--------------------------
Logs each day of forward testing: what signals were generated,
whether they would have hit SL/target, and the running P&L.
This is the bridge between paper trading and going live —
you analyze this log to gain confidence before switching modes.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Date, JSON, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class ForwardTestLog(Base):
    __tablename__ = "forward_test_log"

    id           = Column(Integer, primary_key=True, index=True)
    user_id      = Column(Integer, ForeignKey("users.id"), nullable=False)
    log_date     = Column(Date, nullable=False, index=True)
    strategy     = Column(String(20), default="VCP")

    # Market context on this day
    market_regime   = Column(String(10))   # BULL / CASH / PANIC
    nifty_close     = Column(Float, nullable=True)

    # Signals generated that day
    signals_count   = Column(Integer, default=0)
    signals         = Column(JSON, default=list)   # list of {symbol, entry, sl, quality}

    # Forward test P&L (paper execution of signals)
    trades_entered  = Column(Integer, default=0)
    trades_closed   = Column(Integer, default=0)
    daily_pnl       = Column(Float, default=0.0)
    cumulative_pnl  = Column(Float, default=0.0)
    portfolio_value = Column(Float, nullable=True)

    # Accuracy metrics (filled after trade closes)
    hits_sl         = Column(Integer, default=0)
    hits_target     = Column(Integer, default=0)

    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="forward_logs")

    def __repr__(self):
        return f"<ForwardTestLog {self.log_date} signals={self.signals_count} pnl={self.daily_pnl} user_id={self.user_id}>"
