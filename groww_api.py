"""
groww_api.py
------------
Data fetching: uses yfinance (free, no API key needed, works for NSE)
Order placement: uses Groww API (only needed for live trading)

This means you can run the scanner and backtester RIGHT NOW
without configuring any API key. The Groww API is only needed
when you want to place real buy/sell orders.
"""

import requests
import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config import (
    GROWW_API_KEY, GROWW_SECRET_KEY, GROWW_CLIENT_ID,
    GROWW_BASE_URL
)

logger = logging.getLogger(__name__)


class GrowwAPI:
    """
    Handles market data (via yfinance) and order placement (via Groww API).
    """

    def __init__(self):
        self.api_key    = GROWW_API_KEY
        self.secret_key = GROWW_SECRET_KEY
        self.client_id  = GROWW_CLIENT_ID
        self.session    = requests.Session()
        self._set_headers()

    def _set_headers(self):
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "x-api-key":     self.api_key,
            "Content-Type":  "application/json",
            "Accept":        "application/json"
        })

    def _groww_get(self, endpoint: str, params: dict = None) -> dict:
        url = f"{GROWW_BASE_URL}{endpoint}"
        resp = self.session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _groww_post(self, endpoint: str, payload: dict) -> dict:
        url = f"{GROWW_BASE_URL}{endpoint}"
        resp = self.session.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        return resp.json()

    # ── Market Data via yfinance (free, no API key needed) ───────────────────

    def get_historical_data(self, symbol: str, from_date: str, to_date: str,
                             interval: str = "1d", exchange: str = "NSE") -> list:
        """
        Fetch historical OHLCV data using yfinance.
        NSE symbols on Yahoo Finance use the .NS suffix (e.g. KAYNES.NS).

        Returns list of dicts: [{date, open, high, low, close, volume}, ...]
        """
        yf_symbol = f"{symbol}.NS"
        try:
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(
                start       = from_date,
                end         = to_date,
                interval    = interval,
                auto_adjust = True
            )

            if df.empty:
                logger.warning(f"yfinance: no data for {yf_symbol}")
                return []

            df.reset_index(inplace=True)

            # Flatten MultiIndex columns if present
            if hasattr(df.columns, "levels"):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]

            df.columns = [c.lower().strip() for c in df.columns]

            # Rename datetime -> date
            if "datetime" in df.columns:
                df.rename(columns={"datetime": "date"}, inplace=True)

            # Strip timezone from date column
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)

            # Keep only required columns
            required = ["date", "open", "high", "low", "close", "volume"]
            available = [c for c in required if c in df.columns]
            if "close" not in available:
                logger.warning(f"yfinance: missing 'close' column for {symbol}. Got: {list(df.columns)}")
                return []

            df = df[available].dropna(subset=["close"])
            return df.to_dict(orient="records")

        except Exception as e:
            logger.error(f"yfinance error for {symbol}: {e}")
            return []

    def get_quote(self, symbol: str, exchange: str = "NSE") -> dict:
        """Get the latest quote for a symbol using yfinance."""
        try:
            ticker = yf.Ticker(f"{symbol}.NS")
            info   = ticker.fast_info
            ltp    = float(getattr(info, "last_price", 0) or 0)
            return {
                "symbol":     symbol,
                "ltp":        round(ltp, 2),
                "open":       round(float(getattr(info, "open", 0) or 0), 2),
                "high":       round(float(getattr(info, "day_high", 0) or 0), 2),
                "low":        round(float(getattr(info, "day_low", 0) or 0), 2),
                "prev_close": round(float(getattr(info, "previous_close", 0) or 0), 2),
            }
        except Exception as e:
            logger.error(f"get_quote error for {symbol}: {e}")
            return {"symbol": symbol, "ltp": 0, "error": str(e)}

    def get_index_data(self, days: int = 30) -> pd.DataFrame:
        """
        Fetch BSE Smallcap index for the market filter check.
        Yahoo symbol: ^BSESMCAP
        """
        try:
            end   = datetime.today().strftime("%Y-%m-%d")
            start = (datetime.today() - timedelta(days=days)).strftime("%Y-%m-%d")
            df = yf.download("^BSESMCAP", start=start, end=end,
                             interval="1d", progress=False, auto_adjust=True)
            if df.empty:
                logger.warning("Could not fetch BSE Smallcap index data")
                return pd.DataFrame()

            df.reset_index(inplace=True)
            if hasattr(df.columns, "levels"):
                df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
            df.columns = [c.lower().strip() for c in df.columns]
            if "adj close" in df.columns:
                df.rename(columns={"adj close": "close"}, inplace=True)
            if "date" in df.columns:
                df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None)
                df.set_index("date", inplace=True)
            return df
        except Exception as e:
            logger.warning(f"Index data error: {e}")
            return pd.DataFrame()

    # ── Portfolio & Orders via Groww API (needs key, only for live trading) ──

    def get_funds(self) -> dict:
        """
        Get available funds from Groww.
        IMPORTANT: If you see a 404 error here, your Groww API endpoint path
        may be different. Check https://groww.in/trade-api for the correct URL.
        This error is harmless in paper trading mode.
        """
        return self._groww_get("/user/trading-balance")

    def get_portfolio(self) -> list:
        """Get holdings from Groww."""
        try:
            data = self._groww_get("/portfolio/holdings")
            if isinstance(data, list):
                return data
            return data.get("data", data.get("holdings", []))
        except Exception:
            return []

    def place_order(self, symbol: str, exchange: str, transaction_type: str,
                    quantity: int, order_type: str, price: float = 0.0,
                    trigger_price: float = 0.0, product: str = "CNC") -> dict:
        """
        Place a real order via Groww API.
        Only called when PAPER_TRADING = FALSE in your .env file.
        """
        payload = {
            "symbol":           symbol,
            "exchange":         exchange,
            "transaction_type": transaction_type,
            "quantity":         quantity,
            "order_type":       order_type,
            "price":            price,
            "trigger_price":    trigger_price,
            "product":          product
        }
        logger.info(f"Placing order: {transaction_type} {quantity} {symbol} @ {price}")
        return self._groww_post("/orders", payload)

    def get_orders(self) -> list:
        """Get today's orders from Groww."""
        try:
            data = self._groww_get("/orders")
            if isinstance(data, list):
                return data
            return data.get("data", data.get("orders", []))
        except Exception:
            return []

    # ── Utility ───────────────────────────────────────────────────────────────

    def is_market_open(self) -> bool:
        """Check if NSE is open (9:15 AM to 3:30 PM IST, Mon-Fri)."""
        now = datetime.now()
        if now.weekday() >= 5:
            return False
        open_time  = now.replace(hour=9,  minute=15, second=0, microsecond=0)
        close_time = now.replace(hour=15, minute=30, second=0, microsecond=0)
        return open_time <= now <= close_time

    def test_connection(self) -> bool:
        """
        Test connectivity.
        Data (yfinance) always works without an API key.
        Returns True if yfinance is reachable.
        """
        try:
            hist = yf.Ticker("RELIANCE.NS").history(period="2d", auto_adjust=True)
            if not hist.empty:
                logger.info("Data connection OK (yfinance)")
                return True
        except Exception as e:
            logger.warning(f"yfinance connection test failed: {e}")
        return False