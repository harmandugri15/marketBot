import os
import time
import logging
import requests
import pandas as pd
from datetime import datetime
import pytz
from groww_api import GrowwAPI

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] INTRADAY: %(message)s")
logger = logging.getLogger(__name__)

# Set timezone to India Standard Time (IST)
IST = pytz.timezone('Asia/Kolkata')

def get_ist_now():
    return datetime.now(IST)

def send_telegram_alert(message):
    """Broadcasts a message to your Telegram app."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id: return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try: requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
    except Exception as e: logger.error(f"Telegram failed: {e}")

def get_5m_data(api, symbol):
    """Fetches today's 5-minute data using GrowwAPI and formats it"""
    try:
        raw = api.get_intraday_data(symbol, interval="5m")
        if not raw or len(raw) < 1: 
            return None
            
        # Convert Groww's raw dicts to a pandas DataFrame and rename columns
        df = pd.DataFrame(raw).rename(columns={"c": "close", "v": "volume", "h": "high", "l": "low", "o": "open"})
        
        # Ensure data is numeric
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col])
            
        return df
    except Exception as e:
        logger.error(f"Failed to format 5m data for {symbol}: {e}")
        return None

def calculate_vwap_and_ema(df):
    """Calculates VWAP and 7 EMA on the dataframe"""
    df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
    df['cumulative_vp'] = (df['typical_price'] * df['volume']).cumsum()
    df['cumulative_vol'] = df['volume'].cumsum()
    df['vwap'] = df['cumulative_vp'] / df['cumulative_vol']
    df['ema_7'] = df['close'].ewm(span=7, adjust=False).mean()
    return df

def find_920_setup(api, symbols):
    logger.info("🔍 Scanning for 9:20 AM VWAP + 7 EMA Setups...")
    
    for symbol in symbols:
        df = get_5m_data(api, symbol)
        if df is None or len(df) < 1: continue
        
        df = calculate_vwap_and_ema(df)
        
        # Get the very first candle of the day (9:15 AM to 9:20 AM)
        first_candle = df.iloc[0]
        
        open_p, close_p = first_candle['open'], first_candle['close']
        high_p, low_p = first_candle['high'], first_candle['low']
        vwap = first_candle['vwap']
        ema7 = first_candle['ema_7']
        
        # 🟢 LONG SETUP CONDITIONS
        is_green = close_p > open_p
        vwap_in_body = min(open_p, close_p) <= vwap <= max(open_p, close_p)
        ema_below_price = ema7 < low_p
        
        if is_green and vwap_in_body and ema_below_price:
            logger.info(f"✅ Found LONG Setup on {symbol}")
            return {
                "symbol": symbol, "type": "LONG",
                "trigger_price": round(high_p + 0.10, 2), # Breakout above high
                "stop_loss": round(low_p - 0.10, 2),      # SL below low
                "target": round(high_p + (2 * (high_p - low_p)), 2) # 1:2 R:R
            }
            
        # 🔴 SHORT SETUP CONDITIONS
        is_red = close_p < open_p
        ema_above_price = ema7 > high_p
        
        if is_red and vwap_in_body and ema_above_price:
            logger.info(f"✅ Found SHORT Setup on {symbol}")
            return {
                "symbol": symbol, "type": "SHORT",
                "trigger_price": round(low_p - 0.10, 2),  # Breakdown below low
                "stop_loss": round(high_p + 0.10, 2),     # SL above high
                "target": round(low_p - (2 * (high_p - low_p)), 2) # 1:2 R:R
            }
            
    return None

def run_intraday_engine():
    logger.info("🌅 Intraday Engine Booting Up...")
    
    api = GrowwAPI()
    if not api.connected:
        logger.error("❌ Failed to connect to Groww. Intraday run aborted.")
        send_telegram_alert("🚨 *CRITICAL ERROR*\nFailed to connect to Groww API for Intraday.")
        return
    
    # 1. WAIT UNTIL EXACTLY 9:20 AM IST
    while True:
        now = get_ist_now()
        current_time = now.strftime("%H:%M:%S")
        
        if current_time >= "09:20:05": # Wait 5 seconds extra to ensure data is published by the broker
            break
        elif current_time > "15:00:00":
            logger.error("Market is already closing. Exiting.")
            return
            
        logger.info(f"Waiting for 9:20 AM candle to close... (Current IST: {current_time})")
        time.sleep(15)
        
    # 2. RUN THE SCANNER (Using top liquid Nifty 50 stocks for tight spreads)
    liquid_stocks = [
        "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", 
        "BHARTIARTL", "ITC", "LT", "TATAMOTORS", "AXISBANK", "KOTAKBANK"
    ]
    
    setup = find_920_setup(api, liquid_stocks)
    
    if not setup:
        logger.info("📉 No perfect 9:20 setups found today. Shutting down to protect capital.")
        send_telegram_alert("📉 *INTRADAY UPDATE*\nNo perfect VWAP/EMA setups found today. Staying in cash.")
        return
        
    # We found a setup! Broadcast it to Telegram.
    msg = (
        f"⚡ *INTRADAY SETUP FOUND*\n"
        f"Stock: **{setup['symbol']}** ({setup['type']})\n"
        f"Entry Trigger: Rs {setup['trigger_price']}\n"
        f"Stop Loss: Rs {setup['stop_loss']}\n"
        f"Target (2R): Rs {setup['target']}"
    )
    send_telegram_alert(msg)
    
    # 3. LIVE MONITORING LOOP (Stay awake until 3:15 PM)
    logger.info(f"👀 Monitoring {setup['symbol']} live for trigger...")
    trade_active = False
    
    while get_ist_now().strftime("%H:%M") < "15:15":
        time.sleep(10) # Check live price every 10 seconds
        
        current_price = api.get_live_price(setup['symbol'])
        if not current_price: continue
        
        # ENTRY LOGIC
        if not trade_active:
            if (setup['type'] == "LONG" and current_price >= setup['trigger_price']) or \
               (setup['type'] == "SHORT" and current_price <= setup['trigger_price']):
                trade_active = True
                logger.info("🚀 TRADE EXECUTED!")
                send_telegram_alert(f"🚀 *TRADE EXECUTED*\nEntered {setup['type']} on **{setup['symbol']}** at Rs {current_price}")
                
        # EXIT LOGIC (Stop Loss or Target)
        if trade_active:
            if setup['type'] == "LONG":
                if current_price <= setup['stop_loss']:
                    send_telegram_alert(f"🔴 *STOP LOSS HIT*\nExited {setup['symbol']} at Rs {current_price}")
                    break
                elif current_price >= setup['target']:
                    send_telegram_alert(f"💸 *TARGET HIT*\nSecured 1:2 Profit on {setup['symbol']} at Rs {current_price}!")
                    break
            elif setup['type'] == "SHORT":
                if current_price >= setup['stop_loss']:
                    send_telegram_alert(f"🔴 *STOP LOSS HIT*\nExited {setup['symbol']} at Rs {current_price}")
                    break
                elif current_price <= setup['target']:
                    send_telegram_alert(f"💸 *TARGET HIT*\nSecured 1:2 Profit on {setup['symbol']} at Rs {current_price}!")
                    break

    if trade_active:
        logger.info("🕒 3:15 PM reached. Auto-squaring off any open intraday positions.")
        final_price = api.get_live_price(setup['symbol'])
        send_telegram_alert(f"🕒 *AUTO SQUARE-OFF*\nMarket closing. Closed {setup['symbol']} at Rs {final_price}")

if __name__ == "__main__":
    run_intraday_engine()