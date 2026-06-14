from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # User-specific trading settings
    trading_mode = Column(String(20), default="paper", nullable=False)  # paper, forward, live
    capital = Column(Float, default=200000.0, nullable=False)
    risk_pct = Column(Float, default=1.0, nullable=False)
    max_sl_pct = Column(Float, default=12.0, nullable=False)
    min_quality = Column(Integer, default=85, nullable=False)

    # User-specific Groww API keys
    groww_api_key = Column(String(255), nullable=True)
    groww_secret_key = Column(String(255), nullable=True)
    groww_client_id = Column(String(255), nullable=True)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)

    # Relationships
    trades = relationship("Trade", back_populates="user", cascade="all, delete-orphan")
    forward_logs = relationship("ForwardTestLog", back_populates="user", cascade="all, delete-orphan")
    backtest_results = relationship("BacktestResult", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User {self.username} mode={self.trading_mode}>"
