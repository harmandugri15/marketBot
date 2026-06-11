"""
models/trade.py
---------------
Represents a single trade — paper, forward-test, or live.
The `mode` column is the key safety guard: live trades only flow
through when mode == 'live' and Groww credentials are verified.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum
from sqlalchemy.sql import func
from database import Base
import enum


class TradeMode(str, enum.Enum):
    paper   = "paper"
    forward = "forward"
    live    = "live"


class TradeStatus(str, enum.Enum):
    open     = "open"
    closed   = "closed"
    cancelled = "cancelled"


class Trade(Base):
    __tablename__ = "trades"

    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String(20), nullable=False, index=True)
    strategy    = Column(String(20), default="VCP")
    mode        = Column(Enum(TradeMode), nullable=False, default=TradeMode.paper)
    status      = Column(Enum(TradeStatus), nullable=False, default=TradeStatus.open)

    # Entry
    entry_price  = Column(Float, nullable=False)
    entry_date   = Column(DateTime(timezone=True), server_default=func.now())
    quantity     = Column(Integer, nullable=False)
    stop_loss    = Column(Float, nullable=False)
    target       = Column(Float, nullable=True)

    # Exit
    exit_price   = Column(Float, nullable=True)
    exit_date    = Column(DateTime(timezone=True), nullable=True)
    exit_reason  = Column(String(50), nullable=True)   # SL_HIT / TARGET_HIT / MANUAL / TRAILING

    # P&L
    pnl          = Column(Float, nullable=True)        # in ₹
    pnl_pct      = Column(Float, nullable=True)        # in %

    # Groww order tracking (only for live mode)
    groww_order_id   = Column(String(50), nullable=True)
    groww_order_status = Column(String(20), nullable=True)

    capital_deployed = Column(Float, nullable=True)

    def __repr__(self):
        return f"<Trade {self.symbol} {self.mode} {self.status} pnl={self.pnl}>"
