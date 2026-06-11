"""
config.py
---------
All application configuration via Pydantic Settings.
Values are read from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import Literal


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "MarketBot"
    debug: bool = False
    secret_key: str = Field(default="change-me-in-production", description="JWT secret key")

    # ── Database ─────────────────────────────────────────────────────────────
    # Use sqlite:///./marketbot.db for local, postgres:// for production
    database_url: str = Field(
        default="sqlite:///./marketbot.db",
        description="SQLAlchemy connection string"
    )

    # ── Groww API ─────────────────────────────────────────────────────────────
    groww_api_key: str = ""
    groww_secret_key: str = ""
    groww_client_id: str = ""
    groww_base_url: str = "https://api.groww.in/v1"

    # ── Trading Mode ─────────────────────────────────────────────────────────
    # paper     = simulated fills only
    # forward   = real signals, paper P&L logged (no real orders)
    # live      = real Groww API orders (dangerous — needs valid creds)
    trading_mode: Literal["paper", "forward", "live"] = "paper"

    # ── Capital & Risk ────────────────────────────────────────────────────────
    capital: float = 200000.0       # ₹2,00,000 default
    risk_pct: float = 1.0           # % of capital risked per trade
    max_sl_pct: float = 12.0        # max stop-loss %
    max_trades_per_day: int = 2

    # ── Strategy Parameters ───────────────────────────────────────────────────
    vol_mult: float = 1.5           # volume expansion multiplier
    expansion_pct: float = 4.0      # breakout expansion %
    rsi_oversold: int = 30
    min_quality: int = 85

    # ── Scheduler ────────────────────────────────────────────────────────────
    # Times in IST (UTC+5:30). Cron-style: "hour:minute"
    daily_scan_time: str = "16:00"  # after market close (3:30 PM IST)
    intraday_scan_time: str = "09:20"

    # ── Telegram Alerts (optional) ────────────────────────────────────────────
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ── CORS ─────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]


@lru_cache()
def get_settings() -> Settings:
    """Returns a cached singleton Settings instance."""
    return Settings()


# Stock universe — NSE small/mid-cap for VCP strategy
STOCK_UNIVERSE = [
    "ADANIENT.NS", "ADANIPORTS.NS", "APOLLOHOSP.NS", "ASIANPAINT.NS",
    "AXISBANK.NS", "BAJAJ-AUTO.NS", "BAJFINANCE.NS", "BAJAJFINSV.NS",
    "BPCL.NS", "BHARTIARTL.NS", "BRITANNIA.NS", "CIPLA.NS",
    "COALINDIA.NS", "DIVISLAB.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "GRASIM.NS", "HCLTECH.NS", "HDFCBANK.NS", "HDFCLIFE.NS",
    "HEROMOTOCO.NS", "HINDALCO.NS", "HINDUNILVR.NS", "ICICIBANK.NS",
    "ITC.NS", "INDUSINDBK.NS", "INFY.NS", "JSWSTEEL.NS",
    "KOTAKBANK.NS", "LT.NS", "M&M.NS", "MARUTI.NS",
    "NESTLEIND.NS", "NTPC.NS", "ONGC.NS", "POWERGRID.NS",
    "RELIANCE.NS", "SBILIFE.NS", "SBIN.NS", "SUNPHARMA.NS",
    "TCS.NS", "TATACONSUM.NS", "TATAMOTORS.NS", "TATASTEEL.NS",
    "TECHM.NS", "TITAN.NS", "ULTRACEMCO.NS", "UPL.NS",
    "WIPRO.NS", "ZOMATO.NS",
    # Mid & small cap additions
    "DEEPAKNTR.NS", "ESCORTS.NS", "FEDERALBNK.NS", "GLAND.NS",
    "GODREJPROP.NS", "HAL.NS", "IDEA.NS", "IGL.NS",
    "IRCTC.NS", "JINDALSTEL.NS", "JUBLFOOD.NS", "LICI.NS",
    "LTIM.NS", "MFSL.NS", "MPHASIS.NS", "MRF.NS",
    "NAUKRI.NS", "OBEROIRLTY.NS", "PERSISTENT.NS", "PIIND.NS",
    "POLYCAB.NS", "RECLTD.NS", "SIEMENS.NS", "STAR.NS",
    "TATAELXSI.NS", "TRENT.NS", "UNIONBANK.NS", "VBL.NS",
    "VEDL.NS", "VOLTAS.NS",
]
