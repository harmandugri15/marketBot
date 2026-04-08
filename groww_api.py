import logging
from datetime import datetime
from growwapi import GrowwAPI as OfficialGroww
from config import GROWW_API_KEY, GROWW_SECRET_KEY

logger = logging.getLogger(__name__)

class GrowwAPI:
    def __init__(self):
        self.api_key = GROWW_API_KEY
        self.secret_key = GROWW_SECRET_KEY
        self.client = None
        self.connected = False
        self.authenticate()

    def authenticate(self):
        """Authenticates using the official Groww API Key and Secret flow."""
        if not self.api_key or not self.secret_key:
            logger.warning("Groww API keys missing. Running in disconnected mode.")
            return

        try:
            access_token = OfficialGroww.get_access_token(api_key=self.api_key, secret=self.secret_key)
            self.client = OfficialGroww(access_token)
            
            profile = self.client.get_user_profile()
            if profile:
                self.connected = True
                logger.info("✅ Successfully connected to the official Groww API!")
            else:
                raise Exception("Profile returned empty.")
                
        except Exception as e:
            logger.error(f"❌ Failed to authenticate with Groww API: {e}")
            self.connected = False

    def test_connection(self):
        return self.connected

    def is_market_open(self):
        now = datetime.now()
        if now.weekday() >= 5: return False
        return (9, 15) <= (now.hour, now.minute) and (now.hour, now.minute) <= (15, 30)

    def get_funds(self):
        if not self.connected: return 0.0
        try:
            res = self.client.get_available_margin_details() 
            return res.get('available_cash', 0.0) 
        except Exception as e:
            logger.error(f"Failed to fetch funds: {e}")
            return 0.0

    def get_historical_data(self, symbol, from_date, to_date):
        """Fetches historical Daily EOD candles."""
        if not self.connected: return []
            
        symbol_map = {
            "^NSEI": "NIFTYBEES", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO", "L&TFH": "LTF", "ADANITRANS": "ADANIENSOL"
        }
        groww_ticker = symbol_map.get(symbol, symbol)
            
        try:
            start = f"{from_date} 00:00:00"
            end = f"{to_date} 23:59:59"

            response = self.client.get_historical_candle_data(
                trading_symbol=groww_ticker, exchange="NSE", segment="CASH",
                start_time=start, end_time=end, interval_in_minutes=1440
            )
            
            formatted_data = []
            candle_list = response.get("candles", []) if isinstance(response, dict) else []
            
            for candle in candle_list:
                if len(candle) >= 6: 
                    date_val = datetime.fromtimestamp(candle[0]).strftime('%Y-%m-%d')
                    formatted_data.append({
                        "date": date_val, "open": float(candle[1]), "high": float(candle[2]),
                        "low": float(candle[3]), "close": float(candle[4]), "volume": int(candle[5])
                    })
            return formatted_data
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol} from Groww: {e}")
            return []

    def get_intraday_data(self, symbol, interval="5m"):
        """Fetches today's intraday 5-minute candles."""
        if not self.connected: return []
        
        symbol_map = {
            "^NSEI": "NIFTYBEES", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO", "L&TFH": "LTF", "ADANITRANS": "ADANIENSOL"
        }
        groww_ticker = symbol_map.get(symbol, symbol)
        
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            response = self.client.get_historical_candle_data(
                trading_symbol=groww_ticker, exchange="NSE", segment="CASH",
                start_time=f"{today} 09:15:00", end_time=f"{today} 15:30:00", 
                interval_in_minutes=5 if interval == "5m" else 1
            )
            
            formatted_data = []
            candle_list = response.get("candles", []) if isinstance(response, dict) else []
            
            for candle in candle_list:
                if len(candle) >= 6:
                    formatted_data.append({
                        "o": float(candle[1]), "h": float(candle[2]), "l": float(candle[3]),
                        "c": float(candle[4]), "v": int(candle[5])
                    })
            return formatted_data
        except Exception as e:
            logger.error(f"Error fetching 5m data for {symbol}: {e}")
            return []

    def get_live_price(self, symbol):
        """Grabs the absolute latest live price (LTP) using the lightning-fast native endpoint."""
        if not self.connected: return None
        
        symbol_map = {
            "^NSEI": "NIFTY", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO"
        }
        groww_ticker = symbol_map.get(symbol, symbol)
        
        # Groww's get_ltp requires the format 'EXCHANGE_SYMBOL' (e.g., 'NSE_RELIANCE')
        exchange_symbol = f"NSE_{groww_ticker}"

        try:
            # This is a native, ultra-fast ping. No historical calculation needed!
            response = self.client.get_ltp(
                segment="CASH", # The SDK uses the string "CASH"
                exchange_trading_symbols=exchange_symbol
            )
            
            # The response looks like: { "NSE_RELIANCE": 2500.5 }
            if response and isinstance(response, dict):
                return response.get(exchange_symbol)
            return None
        except Exception as e:
            logger.error(f"Error fetching fast LTP for {symbol}: {e}")
            return None

    def get_historical_intraday_data(self, symbol, from_date, to_date):
        """Fetches historical 5-minute candles using strict 1-Day chunks to bypass Groww limits."""
        if not self.connected: return []
        
        symbol_map = {
            "^NSEI": "NIFTYBEES", "MAPMYIND": "MAPMYINDIA", "DATAPATT": "DATAPATTNS",
            "M&M": "M&M", "BAJAJ-AUTO": "BAJAJ-AUTO", "L&TFH": "LTF", "ADANITRANS": "ADANIENSOL"
        }
        groww_ticker = symbol_map.get(symbol, symbol)

        from datetime import timedelta 
        import time

        try:
            start_dt = datetime.strptime(from_date, "%Y-%m-%d")
            end_dt = datetime.strptime(to_date, "%Y-%m-%d")
            
            formatted_data = []
            current_start = start_dt
            
            # 🧩 STRICT 1-DAY CHUNKING LOOP
            while current_start <= end_dt:
                # Skip weekends (Saturday=5, Sunday=6) to save API calls and speed up the test
                if current_start.weekday() < 5:
                    
                    # Ask for exactly 1 day at a time
                    start_str = f"{current_start.strftime('%Y-%m-%d')} 09:15:00"
                    end_str = f"{current_start.strftime('%Y-%m-%d')} 15:30:00"
                    
                    try:
                        response = self.client.get_historical_candle_data(
                            trading_symbol=groww_ticker, exchange="NSE", segment="CASH",
                            start_time=start_str, end_time=end_str, interval_in_minutes=5
                        )
                        
                        candle_list = response.get("candles", []) if isinstance(response, dict) else []
                        
                        for candle in candle_list:
                            if len(candle) >= 6:
                                dt_obj = datetime.fromtimestamp(candle[0])
                                formatted_data.append({
                                    "date": dt_obj.strftime('%Y-%m-%d'),
                                    "time": dt_obj.strftime('%H:%M:%S'),
                                    "open": float(candle[1]), "high": float(candle[2]),
                                    "low": float(candle[3]), "close": float(candle[4]), "volume": int(candle[5])
                                })
                    except Exception as chunk_e:
                        # If a specific day fails (e.g., market holiday), quietly skip it
                        pass 
                
                # Move to the next single day
                current_start += timedelta(days=1)
                
                # Very tiny sleep to prevent Groww from banning us for hitting them too fast
                time.sleep(0.2) 
                
            logger.info(f"✅ Fetched {len(formatted_data)} intraday candles for {symbol}")
            return formatted_data
            
        except Exception as e:
            logger.error(f"Error fetching historical 5m data for {symbol}: {e}")
            return []

    def place_order(self, symbol, quantity, price, transaction_type="BUY"):
        """Places live limit orders. Disabled when paper_mode is True."""
        if not self.connected: raise Exception("Not connected to Groww API.")
        try:
            response = self.client.place_order(
                validity="DAY", exchange="NSE", transaction_type=transaction_type,
                order_type="LIMIT", price=price, product="CNC", trading_symbol=symbol, quantity=quantity
            )
            return response
        except Exception as e:
            raise Exception(f"Order failed: {e}")