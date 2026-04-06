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
            # Generate the fresh daily access token
            access_token = OfficialGroww.get_access_token(api_key=self.api_key, secret=self.secret_key)
            self.client = OfficialGroww(access_token)
            
            # Verify the connection actually works using the correct SDK method
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
            # Use the correct method for fetching cash balance
            res = self.client.get_available_margin_details() 
            # Note: The exact dict key might be different (e.g., 'available_cash', 'margin'). 
            # If this returns 0 on the dashboard, we will just print the 'res' to find the right key.
            return res.get('available_cash', 0.0) 
        except Exception as e:
            logger.error(f"Failed to fetch funds: {e}")
            return 0.0

    def get_historical_data(self, symbol, from_date, to_date):
        """
        Fetches historical OHLCV data using the unlocked legacy Groww endpoint.
        Includes a dictionary to translate standard symbols to Groww's official NSE names.
        """
        if not self.connected:
            return []
            
        # 🎓 THE TRANSLATION DICTIONARY
        # Maps common/yfinance names to Groww's official NSE Cash market names
        symbol_map = {
            "^NSEI": "NIFTYBEES",      
            "MAPMYIND": "MAPMYINDIA",  # Fixed: Exact NSE ticker
            "DATAPATT": "DATAPATTNS",
            "M&M": "M&M",              # Fixed: Pass special characters raw
            "BAJAJ-AUTO": "BAJAJ-AUTO",# Fixed: Pass dash raw
            "L&TFH": "LTF",
            "ADANITRANS": "ADANIENSOL"
        }

        # Translate the symbol if it is in our map. Otherwise, use the original.
        groww_ticker = symbol_map.get(symbol, symbol)
            
        try:
            # The legacy endpoint requires the exact hours, minutes, and seconds
            start = f"{from_date} 00:00:00"
            end = f"{to_date} 23:59:59"

            # THE BACKDOOR ENDPOINT: get_historical_candle_data (NOT get_historical_candles)
            response = self.client.get_historical_candle_data(
                trading_symbol=groww_ticker,  
                exchange="NSE",
                segment="CASH",
                start_time=start,
                end_time=end,
                interval_in_minutes=1440  # 1440 minutes = 1 Day
            )
            
            formatted_data = []
            
            # The legacy endpoint returns a dictionary with a 'candles' array
            # Format: [timestamp_epoch, open, high, low, close, volume]
            candle_list = response.get("candles", []) if isinstance(response, dict) else []
            
            if not candle_list:
                return []
                
            for candle in candle_list:
                if len(candle) >= 6: # Ensure it has all OHLCV data points
                    # The timestamp is in epoch seconds, we convert it to YYYY-MM-DD
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
            logger.error(f"Error fetching historical data for {symbol} ({groww_ticker}) from Groww: {e}")
            return []

    def place_order(self, symbol, quantity, price, transaction_type="BUY"):
        """Places live limit orders. Disabled when paper_mode is True."""
        if not self.connected:
            raise Exception("Not connected to Groww API. Check credentials.")
            
        try:
            response = self.client.place_order(
                validity="DAY",
                exchange="NSE",
                transaction_type=transaction_type,
                order_type="LIMIT",
                price=price,
                product="CNC", # CNC for Delivery
                trading_symbol=symbol,
                quantity=quantity
            )
            logger.info(f"Order placed successfully: {response}")
            return response
        except Exception as e:
            logger.error(f"Order placement failed: {e}")
            raise Exception(f"Order failed: {e}")