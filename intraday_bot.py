import os
import time
import logging
import requests
from datetime import datetime, timedelta
import pytz
import pandas as pd
from groww_api import GrowwAPI
import forward_test as ft

logging.basicConfig(level=logging.INFO, format="%(asctime)s [INTRADAY]: %(message)s")
logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

# A focused list of highly liquid stocks perfect for intraday
INTRADAY_WATCHLIST = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "TATAMOTORS", "SBIN", "AXISBANK", "M&M", "MARUTI"]

def send_telegram_alert(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            requests.post(url, json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})
        except Exception as e:
            logger.error(f"Telegram failed: {e}")

def push_to_github():
    try:
        os.system('git config --global user.email "bot@marketbot.com"')
        os.system('git config --global user.name "MarketBot Engine"')
        os.system('git add data/forward_test.json')
        os.system('git commit -m "🤖 Auto-update intraday trades" || echo "No changes to commit"')
        os.system('git pull origin main --rebase')
        os.system('git push')
        logger.info("☁️ Pushed live trade updates to GitHub Pages!")
    except Exception as e:
        logger.error(f"Failed to push to GitHub: {e}")

def hunt_vwap_breakouts(api):
    """Scans the watchlist for live VWAP breakouts."""
    logger.info("🔍 Hunting for live VWAP Breakouts...")
    db = ft._load()
    active_symbols = [t["symbol"] for t in db.get("trades", []) if t["status"] in ["ACTIVE", "WATCHING"]]
    
    new_trades = 0
    for symbol in INTRADAY_WATCHLIST:
        if symbol in active_symbols: 
            continue # Already trading this today

        # Fetch 5-min intraday candles
        data = api.get_intraday_data(symbol, "5m")
        if not data or len(data) < 3: 
            continue

        df = pd.DataFrame(data)
        # Calculate VWAP
        df['typical_price'] = (df['h'] + df['l'] + df['c']) / 3
        df['vwap'] = (df['typical_price'] * df['v']).cumsum() / df['v'].cumsum()
        
        last_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]

        # THE STRATEGY: Previous candle was below VWAP, Current candle broke above it!
        if prev_candle['c'] < prev_candle['vwap'] and last_candle['c'] > last_candle['vwap']:
            entry = round(last_candle['c'], 2)
            sl = round(last_candle['l'] * 0.995, 2) # SL just below the breakout candle
            one_r = entry - sl
            
            if one_r > 0 and (one_r / entry * 100) < 3.0: # Keep risk tight (under 3%)
                new_trade = {
                    "id": f"ID_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}",
                    "symbol": symbol,
                    "strategy": "INTRADAY_VWAP",
                    "entry_price": entry,
                    "stop_loss": sl,
                    "sl_pct": round(one_r/entry*100, 2),
                    "shares": int((100000 * 0.02) / one_r) if one_r > 0 else 1, # Assuming 1L cap, 2% risk
                    "status": "WATCHING",
                    "entry_date": None, "exit_date": None, "realized_pnl": 0, "pnl_pct": 0,
                    "notes": "Live VWAP Breakout detected!"
                }
                db.setdefault("trades", []).append(new_trade)
                new_trades += 1
                send_telegram_alert(f"🎯 *LIVE SETUP FOUND:* {symbol} just broke above VWAP at Rs {entry}!")

    if new_trades > 0:
        ft._save(db)
        return True
    return False

def run_intraday_engine():
    send_telegram_alert("⏱️ *Intraday Bot Awakening...* Hunting for live setups all day.")
    
    api = GrowwAPI()
    if not api.connected: 
        logger.error("❌ Groww API not connected.")
        return

    last_hunt_time = datetime.now(IST) - timedelta(minutes=15) # Force hunt immediately

    while True:
        now = datetime.now(IST)
        current_time = now.strftime("%H:%M:%S")
        
        if current_time > "15:20:00":
            send_telegram_alert("🕒 Intraday session over. Closing up shop.")
            push_to_github()
            break

        data_changed = False

        # 1. THE HUNTER: Scan for new setups every 15 minutes
        if (now - last_hunt_time).total_seconds() > 900:
            if hunt_vwap_breakouts(api):
                data_changed = True
            last_hunt_time = now

        # 2. THE EXECUTIONER: Manage active/watching trades
        db = ft._load()
        trades = [t for t in db.get("trades", []) if "INTRADAY" in t["strategy"] and t["status"] != "CLOSED"]
        
        for t in trades:
            live_price = api.get_live_price(t["symbol"])
            if not live_price: continue

            if t["status"] == "WATCHING" and live_price >= t["entry_price"]:
                send_telegram_alert(f"🚀 *INTRADAY ENTRY: {t['symbol']} ({t['strategy']})*\nTriggered at Rs {live_price}!")
                ft.mark_entered(t["id"], live_price)
                data_changed = True
            
            elif t["status"] == "ACTIVE":
                if current_time >= "15:15:00":
                    send_telegram_alert(f"💸 *INTRADAY EXIT: {t['symbol']} ({t['strategy']})*\nAuto Square-off at Rs {live_price}")
                    ft.close_trade(t["id"], live_price, "3:15 Auto Square Off")
                    data_changed = True
                elif live_price <= t["stop_loss"]:
                    send_telegram_alert(f"🔴 *INTRADAY SL HIT: {t['symbol']} ({t['strategy']})*\nExited at Rs {live_price}")
                    ft.close_trade(t["id"], live_price, "Stop Loss Hit")
                    data_changed = True
                elif live_price >= (t["entry_price"] + (2 * (t["entry_price"] - t["stop_loss"]))):
                    # 2R Target Hit!
                    send_telegram_alert(f"🟢 *INTRADAY TARGET HIT: {t['symbol']} ({t['strategy']})*\nExited at Rs {live_price} (2R)")
                    ft.close_trade(t["id"], live_price, "Target Hit (2R)")
                    data_changed = True

        if data_changed:
            push_to_github()

        time.sleep(20)

if __name__ == "__main__":
    run_intraday_engine()