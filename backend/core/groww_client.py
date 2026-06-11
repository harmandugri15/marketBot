"""
core/groww_client.py
--------------------
Clean HTTP client for the Groww Broker API.
Handles authentication, rate limiting, and error normalisation.
All methods return plain Python dicts — no framework coupling.
"""

import logging
import time
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Optional
import requests
from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class GrowwAPIError(Exception):
    """Raised when the Groww API returns an error."""
    def __init__(self, message: str, status_code: int = 0):
        super().__init__(message)
        self.status_code = status_code


class GrowwClient:
    """
    Groww Broker API wrapper.

    Usage:
        client = GrowwClient()
        if client.test_connection():
            data = client.get_historical_data("RELIANCE.NS", "2024-01-01", "2024-12-31")
    """

    BASE_URL = settings.groww_base_url
    _session: Optional[requests.Session] = None

    def __init__(self):
        self.api_key    = settings.groww_api_key
        self.secret_key = settings.groww_secret_key
        self.client_id  = settings.groww_client_id
        self._session   = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "X-Api-Key":    self.api_key,
        })

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.secret_key and self.client_id)

    def _sign(self, payload: str) -> str:
        """HMAC-SHA256 signature for authenticated requests."""
        return hmac.new(
            self.secret_key.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _get(self, path: str, params: dict = None, retries: int = 3) -> dict:
        """GET with exponential backoff retry."""
        url = f"{self.BASE_URL}{path}"
        for attempt in range(retries):
            try:
                resp = self._session.get(url, params=params, timeout=15)
                if resp.status_code == 429:
                    wait = 2 ** attempt
                    logger.warning(f"Rate limited — waiting {wait}s")
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise GrowwAPIError(str(e))
                time.sleep(2 ** attempt)
        return {}

    def _post(self, path: str, body: dict, retries: int = 2) -> dict:
        """POST with retry."""
        url = f"{self.BASE_URL}{path}"
        payload_str = json.dumps(body, separators=(",", ":"))
        headers = {"X-Signature": self._sign(payload_str)}
        for attempt in range(retries):
            try:
                resp = self._session.post(url, data=payload_str, headers=headers, timeout=15)
                resp.raise_for_status()
                return resp.json()
            except requests.exceptions.RequestException as e:
                if attempt == retries - 1:
                    raise GrowwAPIError(str(e))
                time.sleep(2 ** attempt)
        return {}

    def test_connection(self) -> bool:
        """Returns True if API key is valid and connection succeeds."""
        if not self.is_configured:
            return False
        try:
            resp = self._get("/user/profile")
            return "error" not in resp
        except GrowwAPIError:
            return False

    # ── Market Data ───────────────────────────────────────────────────────────

    def get_historical_data(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
        interval: str = "1d",
    ) -> list[dict]:
        """
        Fetch OHLCV data for a symbol.
        Falls back to yfinance if Groww API not configured (ideal for dev/paper mode).
        Returns list of {date, open, high, low, close, volume}.
        """
        if not self.is_configured:
            return self._yfinance_fallback(symbol, from_date, to_date, interval)

        try:
            data = self._get(f"/marketdata/historical/{symbol}", params={
                "from": from_date,
                "to":   to_date,
                "interval": interval,
            })
            return self._normalise_ohlcv(data)
        except GrowwAPIError as e:
            logger.warning(f"Groww API failed for {symbol}, falling back to yfinance: {e}")
            return self._yfinance_fallback(symbol, from_date, to_date, interval)

    def get_ltp(self, symbol: str) -> Optional[float]:
        """Last Traded Price for a symbol."""
        if not self.is_configured:
            return self._yfinance_ltp(symbol)
        try:
            data = self._get(f"/marketdata/ltp/{symbol}")
            return float(data.get("ltp", 0)) or None
        except GrowwAPIError:
            return self._yfinance_ltp(symbol)

    def get_quote(self, symbol: str) -> dict:
        """Full bid/ask quote."""
        return self._get(f"/marketdata/quote/{symbol}")

    # ── Order Management ──────────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        side: str,          # "BUY" | "SELL"
        quantity: int,
        order_type: str,    # "MARKET" | "LIMIT"
        price: float = 0,
        trigger_price: float = 0,
        product: str = "CNC",  # CNC = delivery, MIS = intraday
    ) -> dict:
        """
        Place a real order via Groww.
        NEVER call this in paper or forward mode — guarded by trade_service.
        """
        body = {
            "symbol":        symbol,
            "side":          side,
            "quantity":      quantity,
            "order_type":    order_type,
            "product":       product,
            "price":         price,
            "trigger_price": trigger_price,
            "timestamp":     int(time.time() * 1000),
        }
        logger.info(f"LIVE ORDER: {side} {quantity} x {symbol} @ {price or 'MARKET'}")
        return self._post("/order/place", body)

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an open order."""
        return self._post("/order/cancel", {"order_id": order_id})

    def get_order_status(self, order_id: str) -> dict:
        """Get status of a placed order."""
        return self._get(f"/order/{order_id}")

    def get_positions(self) -> list[dict]:
        """Fetch open positions."""
        data = self._get("/portfolio/positions")
        return data.get("positions", [])

    def get_holdings(self) -> list[dict]:
        """Fetch long-term holdings."""
        data = self._get("/portfolio/holdings")
        return data.get("holdings", [])

    # ── yfinance Fallback (Paper / Forward / Dev Mode) ────────────────────────

    @staticmethod
    def _yfinance_fallback(
        symbol: str,
        from_date: str,
        to_date: str,
        interval: str = "1d",
    ) -> list[dict]:
        """Use yfinance when Groww API is not configured."""
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            df = ticker.history(start=from_date, end=to_date, interval=interval)
            if df.empty:
                return []
            df.index = df.index.tz_localize(None) if df.index.tz else df.index
            records = []
            for ts, row in df.iterrows():
                records.append({
                    "date":   ts.strftime("%Y-%m-%d"),
                    "open":   round(float(row["Open"]), 2),
                    "high":   round(float(row["High"]), 2),
                    "low":    round(float(row["Low"]), 2),
                    "close":  round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            return records
        except Exception as e:
            logger.error(f"yfinance fallback failed for {symbol}: {e}")
            return []

    @staticmethod
    def _yfinance_ltp(symbol: str) -> Optional[float]:
        """Get last price via yfinance."""
        try:
            import yfinance as yf
            data = yf.Ticker(symbol).fast_info
            return float(data.last_price) if data.last_price else None
        except Exception:
            return None

    @staticmethod
    def _normalise_ohlcv(raw: dict | list) -> list[dict]:
        """Convert Groww API response format to standard {date, open, high, low, close, volume}."""
        if isinstance(raw, list):
            return raw
        candles = raw.get("candles", raw.get("data", []))
        result = []
        for c in candles:
            if isinstance(c, dict):
                result.append({
                    "date":   c.get("date", c.get("timestamp", "")),
                    "open":   float(c.get("o", c.get("open", 0))),
                    "high":   float(c.get("h", c.get("high", 0))),
                    "low":    float(c.get("l", c.get("low", 0))),
                    "close":  float(c.get("c", c.get("close", 0))),
                    "volume": int(c.get("v", c.get("volume", 0))),
                })
        return result
