"""
core/groww_client.py
--------------------
Clean HTTP client wrapper that uses the official Groww Broker API SDK.
Handles authentication, rate limiting, and error normalisation.
All methods return plain Python dicts — no framework coupling.
"""

import logging
import time
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
    Groww Broker API wrapper using the official SDK.

    Usage:
        client = GrowwClient()
        if client.test_connection():
            data = client.get_historical_data("RELIANCE.NS", "2024-01-01", "2024-12-31")
    """

    _global_auth_failed = False

    def __init__(self, api_key: str = None, secret_key: str = None, client_id: str = None):
        self.api_key    = api_key or settings.groww_api_key
        self.secret_key = secret_key or settings.groww_secret_key
        self.client_id  = client_id or settings.groww_client_id
        
        self.client = None
        self.connected = False
        self.market_data_allowed = True
        
        self.authenticate()

    def authenticate(self):
        """Authenticates using the official Groww API Key and Secret flow."""
        if not self.api_key or not self.secret_key:
            logger.info("Groww API credentials not set. Running in yfinance fallback mode.")
            return
            
        if GrowwClient._global_auth_failed:
            self.connected = False
            return

        try:
            from growwapi import GrowwAPI as OfficialGroww
            logger.info("Generating Groww API access token...")
            access_token = OfficialGroww.get_access_token(api_key=self.api_key, secret=self.secret_key)
            if access_token:
                self.client = OfficialGroww(access_token)
                # Try to fetch user profile to verify connection
                profile = None
                if hasattr(self.client, "get_user_profile"):
                    profile = self.client.get_user_profile()
                elif hasattr(self.client, "get_profile"):
                    profile = self.client.get_profile()
                
                self.connected = True
                logger.info("✅ Successfully connected to the official Groww API SDK!")
            else:
                logger.error("❌ Groww API get_access_token returned empty token.")
                self.connected = False
                GrowwClient._global_auth_failed = True
        except ImportError:
            logger.error("❌ growwapi package not installed. Run 'pip install growwapi'")
            self.connected = False
        except Exception as e:
            logger.error(f"❌ Failed to authenticate with Groww API SDK: {e}")
            self.connected = False
            GrowwClient._global_auth_failed = True

    @property
    def is_configured(self) -> bool:
        """Returns True if the client is authenticated and connected to Groww."""
        return self.connected

    def test_connection(self) -> bool:
        """Returns True if connection is active."""
        return self.connected

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
        if not self.is_configured or not self.client or not self.market_data_allowed:
            return self._yfinance_fallback(symbol, from_date, to_date, interval)

        # Clean symbol by stripping .NS suffix for Groww API
        clean_symbol = symbol.replace(".NS", "")
        symbol_map = {
            "^NSEI": "NIFTYBEES", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO", "L&TFH": "LTF", "ADANITRANS": "ADANIENSOL"
        }
        groww_ticker = symbol_map.get(clean_symbol, clean_symbol)

        try:
            start_str = f"{from_date} 00:00:00"
            end_str = f"{to_date} 23:59:59"
            
            # Map interval to minutes
            interval_mins = 1440
            if interval == "5m":
                interval_mins = 5
            elif interval == "15m":
                interval_mins = 15
            elif interval == "1h":
                interval_mins = 60

            response = self.client.get_historical_candle_data(
                trading_symbol=groww_ticker,
                exchange="NSE",
                segment="CASH",
                start_time=start_str,
                end_time=end_str,
                interval_in_minutes=interval_mins
            )

            formatted_data = []
            candle_list = response.get("candles", []) if isinstance(response, dict) else []
            for candle in candle_list:
                if len(candle) >= 6:
                    date_val = datetime.fromtimestamp(candle[0]).strftime('%Y-%m-%d')
                    formatted_data.append({
                        "date": date_val,
                        "open": float(candle[1]),
                        "high": float(candle[2]),
                        "low": float(candle[3]),
                        "close": float(candle[4]),
                        "volume": int(candle[5])
                    })
            return formatted_data
        except Exception as e:
            err_msg = str(e)
            if "forbidden" in err_msg.lower() or "403" in err_msg:
                self.market_data_allowed = False
                logger.info("🚫 Groww API returned Access Forbidden for market data (unpaid account). "
                            "Switching permanently to silent yfinance fallback mode for this session.")
            else:
                logger.warning(f"Groww API failed for {symbol}, falling back to yfinance: {e}")
            return self._yfinance_fallback(symbol, from_date, to_date, interval)

    def get_historical_intraday_data(
        self,
        symbol: str,
        from_date: str,
        to_date: str,
    ) -> list[dict]:
        """
        Fetch historical 5-minute candles for a symbol.
        Falls back to yfinance if Groww API not configured.
        Returns list of {date, time, open, high, low, close, volume}.
        """
        if not self.is_configured or not self.client or not self.market_data_allowed:
            return self._yfinance_historical_intraday(symbol, from_date, to_date)

        clean_symbol = symbol.replace(".NS", "")
        symbol_map = {
            "^NSEI": "NIFTYBEES", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO", "L&TFH": "LTF", "ADANITRANS": "ADANIENSOL"
        }
        groww_ticker = symbol_map.get(clean_symbol, clean_symbol)

        try:
            start_dt = datetime.strptime(from_date, "%Y-%m-%d")
            end_dt = datetime.strptime(to_date, "%Y-%m-%d")
            
            formatted_data = []
            current_start = start_dt
            
            # STRICT 1-DAY CHUNKING LOOP TO BYPASS LIMITS
            while current_start <= end_dt:
                if current_start.weekday() < 5:
                    start_str = f"{current_start.strftime('%Y-%m-%d')} 09:15:00"
                    end_str = f"{current_start.strftime('%Y-%m-%d')} 15:30:00"
                    
                    try:
                        response = self.client.get_historical_candle_data(
                            trading_symbol=groww_ticker,
                            exchange="NSE",
                            segment="CASH",
                            start_time=start_str,
                            end_time=end_str,
                            interval_in_minutes=5
                        )
                        
                        candle_list = response.get("candles", []) if isinstance(response, dict) else []
                        for candle in candle_list:
                            if len(candle) >= 6:
                                dt_obj = datetime.fromtimestamp(candle[0])
                                formatted_data.append({
                                    "date":   dt_obj.strftime('%Y-%m-%d'),
                                    "time":   dt_obj.strftime('%H:%M:%S'),
                                    "open":   float(candle[1]),
                                    "high":   float(candle[2]),
                                    "low":    float(candle[3]),
                                    "close":  float(candle[4]),
                                    "volume": int(candle[5])
                                })
                    except Exception as e:
                        err_msg = str(e)
                        if "forbidden" in err_msg.lower() or "403" in err_msg:
                            self.market_data_allowed = False
                            logger.info("🚫 Groww API returned Access Forbidden for market data (unpaid account). "
                                        "Switching permanently to silent yfinance fallback mode for this session.")
                            return self._yfinance_historical_intraday(symbol, from_date, to_date)
                        pass
                
                current_start += timedelta(days=1)
                time.sleep(0.2)
                
            if not formatted_data:
                logger.warning(f"No Groww intraday data fetched for {symbol}, falling back to yfinance")
                return self._yfinance_historical_intraday(symbol, from_date, to_date)
            return formatted_data
        except Exception as e:
            logger.warning(f"Groww API intraday failed for {symbol}: {e}. Falling back to yfinance.")
            return self._yfinance_historical_intraday(symbol, from_date, to_date)

    def get_ltp(self, symbol: str) -> Optional[float]:
        """Last Traded Price for a symbol."""
        if not self.is_configured or not self.client or not self.market_data_allowed:
            return self._yfinance_ltp(symbol)
        clean_symbol = symbol.replace(".NS", "")
        symbol_map = {
            "^NSEI": "NIFTYBEES", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO", "L&TFH": "LTF", "ADANITRANS": "ADANIENSOL"
        }
        groww_ticker = symbol_map.get(clean_symbol, clean_symbol)
        exchange_symbol = f"NSE_{groww_ticker}"
        try:
            response = self.client.get_ltp(
                segment="CASH",
                exchange_trading_symbols=exchange_symbol
            )
            if response and isinstance(response, dict):
                val = response.get(exchange_symbol)
                if val is not None:
                    return float(val)
            return self._yfinance_ltp(symbol)
        except Exception as e:
            err_msg = str(e)
            if "forbidden" in err_msg.lower() or "403" in err_msg:
                self.market_data_allowed = False
                logger.info("🚫 Groww API returned Access Forbidden for market data (unpaid account). "
                            "Switching permanently to silent yfinance fallback mode for this session.")
            return self._yfinance_ltp(symbol)

    def get_quote(self, symbol: str) -> dict:
        """Full bid/ask quote."""
        if not self.is_configured or not self.client or not self.market_data_allowed:
            return {}
        clean_symbol = symbol.replace(".NS", "")
        symbol_map = {
            "^NSEI": "NIFTYBEES", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO", "L&TFH": "LTF", "ADANITRANS": "ADANIENSOL"
        }
        groww_ticker = symbol_map.get(clean_symbol, clean_symbol)
        try:
            if hasattr(self.client, "get_quote"):
                return self.client.get_quote(trading_symbol=groww_ticker, exchange="NSE", segment="CASH")
            return {}
        except Exception as e:
            err_msg = str(e)
            if "forbidden" in err_msg.lower() or "403" in err_msg:
                self.market_data_allowed = False
                logger.info("🚫 Groww API returned Access Forbidden for market data (unpaid account). "
                            "Switching permanently to silent yfinance fallback mode for this session.")
            return {}

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
        """Place a real order via Groww."""
        if not self.is_configured or not self.client:
            raise Exception("Groww API not configured or not connected")
            
        clean_symbol = symbol.replace(".NS", "")
        symbol_map = {
            "^NSEI": "NIFTYBEES", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO", "L&TFH": "LTF", "ADANITRANS": "ADANIENSOL"
        }
        groww_ticker = symbol_map.get(clean_symbol, clean_symbol)
        
        logger.info(f"LIVE ORDER: {side} {quantity} x {groww_ticker} @ {price or 'MARKET'}")
        
        kwargs = {
            "validity": "DAY",
            "exchange": "NSE",
            "transaction_type": side,
            "order_type": order_type,
            "product": product,
            "trading_symbol": groww_ticker,
            "quantity": quantity
        }
        if price:
            kwargs["price"] = price
        if trigger_price:
            kwargs["trigger_price"] = trigger_price
            
        try:
            return self.client.place_order(**kwargs)
        except Exception as e:
            raise GrowwAPIError(str(e))

    def cancel_order(self, order_id: str) -> dict:
        """Cancel an open order."""
        if not self.is_configured or not self.client:
            raise Exception("Groww API not configured")
        try:
            return self.client.cancel_order(order_id=order_id)
        except Exception as e:
            raise GrowwAPIError(str(e))

    def get_order_status(self, order_id: str) -> dict:
        """Get status of a placed order."""
        if not self.is_configured or not self.client:
            raise Exception("Groww API not configured")
        try:
            return self.client.get_order_status(order_id=order_id)
        except Exception as e:
            raise GrowwAPIError(str(e))

    def get_positions(self) -> list[dict]:
        """Fetch open positions."""
        if not self.is_configured or not self.client:
            return []
        try:
            return self.client.get_positions_for_user()
        except Exception as e:
            logger.error(f"Failed to fetch positions: {e}")
            return []

    def get_holdings(self) -> list[dict]:
        """Fetch long-term holdings."""
        if not self.is_configured or not self.client:
            return []
        try:
            return self.client.get_holdings_for_user()
        except Exception as e:
            logger.error(f"Failed to fetch holdings: {e}")
            return []

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
            from datetime import datetime, timedelta
            import yfinance as yf
            yf_symbol = symbol
            if not yf_symbol.endswith(".NS") and not yf_symbol.startswith("^"):
                yf_symbol = f"{yf_symbol}.NS"
                
            # yfinance limits
            start_dt = datetime.strptime(from_date, "%Y-%m-%d")
            today_dt = datetime.now()
            if interval in ["5m", "15m"]:
                max_start = today_dt - timedelta(days=59)
                if start_dt < max_start:
                    logger.warning(f"[yfinance] Interval {interval} restricted to last 60 days. Adjusting from_date.")
                    start_dt = max_start
                    from_date = start_dt.strftime("%Y-%m-%d")
            elif interval in ["1h"]:
                max_start = today_dt - timedelta(days=729)
                if start_dt < max_start:
                    logger.warning(f"[yfinance] Interval {interval} restricted to last 730 days. Adjusting from_date.")
                    start_dt = max_start
                    from_date = start_dt.strftime("%Y-%m-%d")
                    
            logger.info(f"[yfinance] Fetching {symbol} {interval} {from_date}\u2192{to_date}")
            t0 = time.time()
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(start=from_date, end=to_date, interval=interval)
            if df.empty:
                logger.warning(f"[yfinance] {symbol}: 0 candles returned (possibly delisted or no data)")
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
            elapsed = time.time() - t0
            logger.info(f"[yfinance] {symbol}: {len(records)} candles fetched in {elapsed:.2f}s")
            return records
        except Exception as e:
            logger.error(f"yfinance fallback failed for {symbol}: {e}")
            return []

    @staticmethod
    def _yfinance_historical_intraday(
        symbol: str,
        from_date: str,
        to_date: str,
    ) -> list[dict]:
        """Use yfinance to fetch 5m intraday data."""
        try:
            import yfinance as yf
            yf_symbol = symbol
            if not yf_symbol.endswith(".NS") and not yf_symbol.startswith("^"):
                yf_symbol = f"{yf_symbol}.NS"
            logger.info(f"[yfinance] Fetching {symbol} 5m intraday {from_date}\u2192{to_date}")
            t0 = time.time()
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(start=from_date, end=to_date, interval="5m")
            if df.empty:
                logger.warning(f"[yfinance] {symbol}: 0 candles returned (possibly delisted or no data)")
                return []
            
            df.index = df.index.tz_convert("Asia/Kolkata") if df.index.tz else df.index.tz_localize("Asia/Kolkata")
            
            records = []
            for ts, row in df.iterrows():
                records.append({
                    "date":   ts.strftime("%Y-%m-%d"),
                    "time":   ts.strftime("%H:%M:%S"),
                    "open":   round(float(row["Open"]), 2),
                    "high":   round(float(row["High"]), 2),
                    "low":    round(float(row["Low"]), 2),
                    "close":  round(float(row["Close"]), 2),
                    "volume": int(row["Volume"]),
                })
            elapsed = time.time() - t0
            logger.info(f"[yfinance] {symbol}: {len(records)} candles fetched in {elapsed:.2f}s")
            return records
        except Exception as e:
            logger.error(f"yfinance 5m fallback failed for {symbol}: {e}")
            return []

    @staticmethod
    def _yfinance_ltp(symbol: str) -> Optional[float]:
        """Get last price via yfinance."""
        try:
            import yfinance as yf
            yf_symbol = symbol
            if not yf_symbol.endswith(".NS") and not yf_symbol.startswith("^"):
                yf_symbol = f"{yf_symbol}.NS"
            data = yf.Ticker(yf_symbol).fast_info
            price = float(data.last_price) if data.last_price else None
            if price is not None:
                logger.info(f"[yfinance] LTP {symbol}: {price}")
            return price
        except Exception:
            return None
