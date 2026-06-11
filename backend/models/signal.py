"""
models/signal.py
----------------
VCP / strategy signal record produced by the daily scanner.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from database import Base


class Signal(Base):
    __tablename__ = "signals"

    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String(20), nullable=False, index=True)
    strategy    = Column(String(20), nullable=False, default="VCP")  # VCP / INTRADAY / SWING

    # Price levels
    close       = Column(Float, nullable=False)
    entry       = Column(Float, nullable=False)
    stop_loss   = Column(Float, nullable=False)
    target      = Column(Float, nullable=True)

    # Quality score (0–100)
    quality     = Column(Integer, default=0)

    # Indicators snapshot
    rsi         = Column(Float, nullable=True)
    vol_ratio   = Column(Float, nullable=True)   # today vol / 50-day avg
    pullback_pct= Column(Float, nullable=True)
    market_regime = Column(String(10), nullable=True)  # BULL / CASH / PANIC

    # Metadata
    scan_date   = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_active   = Column(Boolean, default=True)
    notes       = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Signal {self.symbol} @ {self.entry} SL={self.stop_loss} Q={self.quality}>"
