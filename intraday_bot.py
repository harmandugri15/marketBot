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

# Highly liquid stocks perfect for VWAP Bounces
INTRADAY_WATCHLIST = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "TATAMOTORS", "SBIN", "AXISBANK", "M&M", "MARUTI"]

# STUDENT ACCOUNT SETTINGS
STUDENT_CAPITAL = 4000.0  # Base capital
MIS_LEVERAGE = 5.0        # 5x Margin for Intraday
RISK_PCT = 2.0            # Risk 2% of Base Capital (Rs 80)

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

def hunt_vwap_bounces(api):
    """Scans the watchlist for high-probability morning VWAP bounces."""
    logger.info("🔍 Hunting for Leveraged VWAP Bounces...")
    db = ft._load()
    active_symbols = [t["symbol"] for t in db.get("trades", []) if t["status"] in ["ACTIVE", "WATCHING"]]
    
    new_trades = 0
    for symbol in INTRADAY_WATCHLIST:
        if symbol in active_symbols: 
            continue 

        # Fetch 5-min intraday candles
        data = api.get_intraday_data(symbol, "5m")
        if not data or len(data) < 3: 
            continue

        df = pd.DataFrame(data)
        
        # Calculate Live VWAP
        df['typical_price'] = (df['h'] + df['l'] + df['c']) / 3
        df['vwap'] = (df['typical_price'] * df['v']).cumsum() / df['v'].cumsum()
        
        day_open = df.iloc[0]['o']
        curr_candle = df.iloc[-1]
        prev_candle = df.iloc[-2]
        
        distance_to_vwap = abs(prev_candle['l'] - prev_candle['vwap']) / prev_candle['vwap']

        # THE STRATEGY: Morning VWAP Bounce
        if curr_candle['c'] > day_open and distance_to_vwap < 0.002:
            if curr_candle['c'] > curr_candle['o']: # Green Confirmation
                
                entry = round(curr_candle['c'], 2)
                sl = round(curr_candle['vwap'] * 0.998, 2)
                one_r = entry - sl
                
                # Strict Risk Control: Max 1.5% SL width
                if one_r > 0 and (one_r / entry * 100) < 1.5:
                    
                    # 5X LEVERAGE MATH
                    risk_amt = STUDENT_CAPITAL * (RISK_PCT / 100)
                    desired_shares = int(risk_amt / one_r) if one_r > 0 else 1
                    max_affordable = int((STUDENT_CAPITAL * MIS_LEVERAGE) / entry)
                    shares = min(desired_shares, max_affordable)
                    
                    if shares > 0:
                        new_trade = {
                            "id": f"ID_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}",
                            "symbol": symbol,
                            "strategy": "VWAP_RUNNER_5X",
                            "entry_price": entry,
                            "stop_loss": sl,
                            "one_r": round(one_r, 2),
                            "sl_pct": round(one_r/entry*100, 2),
                            "shares": shares, 
                            "status": "WATCHING",
                            "entry_date": None, "exit_date": None, "realized_pnl": 0, "pnl_pct": 0,
                            "notes": f"Leveraged VWAP Bounce. Target: Infinite Trail."
                        }
                        db.setdefault("trades", []).append(new_trade)
                        new_trades += 1
                        send_telegram_alert(f"🎯 *LIVE SETUP: {symbol} (5X LEVERAGE)*\nVWAP Bounce detected! Entry at Rs {entry}.")

    if new_trades > 0:
        ft._save(db)
        return True
    return False

def run_intraday_engine():
    send_telegram_alert(f"⏱️ *Student Engine Awakening...* Base Capital: Rs {STUDENT_CAPITAL} | Buying Power: Rs {STUDENT_CAPITAL * MIS_LEVERAGE}")
    
    api = GrowwAPI()
    if not api.connected: 
        logger.error("❌ Groww API not connected.")
        return

    last_hunt_time = datetime.now(IST) - timedelta(minutes=15) 
    alerted_today = set() 

    while True:
        now = datetime.now(IST)
        current_time = now.strftime("%H:%M:%S")
        
        # Hard Stop at 2:50 PM
        if current_time > "14:50:00":
            send_telegram_alert("🕒 Intraday session over. All positions should be clear.")
            push_to_github()
            break

        data_changed = False

        # 1. THE HUNTER: Scan 9:35 AM to 11:30 AM every 5 minutes
        if "09:35:00" <= current_time <= "11:30:00":
            if (now - last_hunt_time).total_seconds() > 300:
                if hunt_vwap_bounces(api):
                    data_changed = True
                last_hunt_time = now

        # 2. THE EXECUTIONER: Manage active/watching trades
        db = ft._load()
        trades = [t for t in db.get("trades", []) if "VWAP_RUNNER" in t["strategy"] and t["status"] != "CLOSED"]
        
        for t in trades:
            live_price = api.get_live_price(t["symbol"])
            if not live_price: continue

            trade_id = t["id"]
            one_r = t.get("one_r", abs(t["entry_price"] - t["stop_loss"]))

            # --- ENTRY TRIGGER ---
            if t["status"] == "WATCHING" and live_price >= t["entry_price"]:
                if trade_id not in alerted_today:
                    send_telegram_alert(f"🚀 *ORDER FILLED: {t['symbol']}*\nBought {t['shares']} shares at Rs {live_price}!")
                    alerted_today.add(trade_id)
                ft.mark_entered(trade_id, live_price)
                data_changed = True
            
            # --- ACTIVE TRAILING & EXITS ---
            elif t["status"] == "ACTIVE":
                
                # Auto Square-Off at 2:45 PM
                if current_time >= "14:45:00":
                    if trade_id not in alerted_today:
                        send_telegram_alert(f"💸 *END OF DAY: {t['symbol']}*\nAuto Square-off at Rs {live_price}")
                        alerted_today.add(trade_id)
                    ft.close_trade(trade_id, live_price, "14:45 Auto Square Off")
                    data_changed = True
                    continue

                # Fetch Live VWAP for trailing
                live_vwap = t["stop_loss"]
                data = api.get_intraday_data(t["symbol"], "5m")
                if data and len(data) > 0:
                    df = pd.DataFrame(data)
                    df['typical_price'] = (df['h'] + df['l'] + df['c']) / 3
                    df['vwap'] = (df['typical_price'] * df['v']).cumsum() / df['v'].cumsum()
                    live_vwap = df.iloc[-1]['vwap']

                new_sl = t["stop_loss"]

                # Trailing Rule 1: 2R = Break Even (Risk Free Trade)
                if live_price >= t["entry_price"] + (2 * one_r) and new_sl < t["entry_price"]:
                    new_sl = t["entry_price"]
                    send_telegram_alert(f"🛡️ *RISK FREE: {t['symbol']}*\n2R Hit! Stop Loss moved to Break Even.")

                # Trailing Rule 2: Ride the VWAP
                if new_sl >= t["entry_price"] and live_vwap > new_sl:
                    trail_sl = round(live_vwap * 0.998, 2)
                    if trail_sl > new_sl:
                        new_sl = trail_sl
                
                if new_sl != t["stop_loss"]:
                    t["stop_loss"] = new_sl
                    data_changed = True

                # Exit Trigger (Hit Stop Loss or Trailed Stop)
                if live_price <= t["stop_loss"]:
                    reason = "Trailed Profit Blocked" if t["stop_loss"] >= t["entry_price"] else "Stop Loss Hit"
                    
                    # Prevent duplicate alerts
                    alert_key = f"{trade_id}_exit"
                    if alert_key not in alerted_today:
                        send_telegram_alert(f"🔴 *TRADE CLOSED: {t['symbol']}*\n{reason} at Rs {live_price}")
                        alerted_today.add(alert_key)
                        
                    ft.close_trade(trade_id, live_price, reason)
                    data_changed = True

        if data_changed:
            ft._save(db)
            push_to_github()

        time.sleep(20)

if __name__ == "__main__":
    run_intraday_engine()