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

def hunt_inside_candles(api):
    """Scans the watchlist for high-probability Inside Candle setups."""
    logger.info("🔍 Hunting for 5m Inside Candle Setups...")
    db = ft._load()
    active_symbols = [t["symbol"] for t in db.get("trades", []) if t["status"] in ["ACTIVE", "WATCHING"]]
    
    new_trades = 0
    for symbol in INTRADAY_WATCHLIST:
        if symbol in active_symbols: 
            continue # Already tracking a setup for this stock today

        # Fetch 5-min intraday candles
        data = api.get_intraday_data(symbol, "5m")
        if not data or len(data) < 4: 
            continue

        df = pd.DataFrame(data)
        
        # Define the candles (-1 is the LIVE forming candle, we only scan completed candles)
        mother = df.iloc[-3]
        inside = df.iloc[-2]
        
        # Initial Trend Filter: Day's Open vs Current Price
        day_open = df.iloc[0]['o']
        current_close = inside['c']
        bias = "LONG" if current_close > day_open else "SHORT"

        # STRATEGY RULE 1: Is it an Inside Candle?
        if inside['h'] < mother['h'] and inside['l'] > mother['l']:
            
            # STRATEGY RULE 2: Body Size Filter (Inside body must be < 60% of Mother's range)
            inside_body = abs(inside['c'] - inside['o'])
            mother_range = mother['h'] - mother['l']
            
            if inside_body < (0.6 * mother_range):
                
                # STRATEGY RULE 3: Setup Entry and SL based on Trend Bias
                if bias == "LONG":
                    entry = round(inside['h'] + 0.05, 2) # Trigger just above the inside high
                    sl = round(min(inside['l'], mother['l']), 2) # Safety SL rule
                    one_r = entry - sl
                else: # SHORT (If your broker/API supports intraday shorting)
                    entry = round(inside['l'] - 0.05, 2) # Trigger just below the inside low
                    sl = round(max(inside['h'], mother['h']), 2) # Safety SL rule
                    one_r = sl - entry
                
                # Risk Management Filter
                if one_r > 0 and (one_r / entry * 100) < 2.0: # Keep risk under 2%
                    new_trade = {
                        "id": f"ID_{symbol}_{datetime.now().strftime('%Y%m%d%H%M')}",
                        "symbol": symbol,
                        "strategy": f"INTRADAY_INSIDE_{bias}",
                        "trade_type": bias, # Tag for executioner
                        "entry_price": entry,
                        "stop_loss": sl,
                        "sl_pct": round(one_r/entry*100, 2),
                        "shares": int((100000 * 0.02) / one_r) if one_r > 0 else 1,
                        "status": "WATCHING",
                        "entry_date": None, "exit_date": None, "realized_pnl": 0, "pnl_pct": 0,
                        "notes": f"Inside Candle {bias} setup. Body size optimized."
                    }
                    db.setdefault("trades", []).append(new_trade)
                    new_trades += 1
                    send_telegram_alert(f"🎯 *LIVE SETUP FOUND: {symbol} (INSIDE {bias})*\nMother-Baby pattern formed! Trigger at Rs {entry}.")

    if new_trades > 0:
        ft._save(db)
        return True
    return False

def run_intraday_engine():
    send_telegram_alert("⏱️ *Intraday Engine Awakening...* Hunting 5m Inside Candles.")
    
    api = GrowwAPI()
    if not api.connected: 
        logger.error("❌ Groww API not connected.")
        return

    last_hunt_time = datetime.now(IST) - timedelta(minutes=15) # Force hunt immediately
    alerted_today = set() # Anti-Spam Memory Shield

    while True:
        now = datetime.now(IST)
        current_time = now.strftime("%H:%M:%S")
        
        if current_time > "15:20:00":
            send_telegram_alert("🕒 Intraday session over. Closing up shop.")
            push_to_github()
            break

        data_changed = False

        # 1. THE HUNTER: Scan for new setups every 5 minutes (300 seconds)
        if (now - last_hunt_time).total_seconds() > 300:
            if hunt_inside_candles(api):
                data_changed = True
            last_hunt_time = now

        # 2. THE EXECUTIONER: Manage active/watching trades
        db = ft._load()
        trades = [t for t in db.get("trades", []) if "INTRADAY_INSIDE" in t["strategy"] and t["status"] != "CLOSED"]
        
        for t in trades:
            live_price = api.get_live_price(t["symbol"])
            if not live_price: continue

            trade_id = t["id"]
            trade_type = t.get("trade_type", "LONG")
            one_r = abs(t["entry_price"] - t["stop_loss"])

            # --- ENTRY LOGIC ---
            if t["status"] == "WATCHING":
                triggered = (trade_type == "LONG" and live_price >= t["entry_price"]) or \
                            (trade_type == "SHORT" and live_price <= t["entry_price"])
                
                if triggered:
                    if trade_id not in alerted_today:
                        send_telegram_alert(f"🚀 *INTRADAY ENTRY: {t['symbol']} ({t['strategy']})*\nTriggered breakout at Rs {live_price}!")
                        alerted_today.add(trade_id)
                    ft.mark_entered(trade_id, live_price)
                    data_changed = True
            
            # --- ACTIVE MANAGEMENT LOGIC ---
            elif t["status"] == "ACTIVE":
                if current_time >= "15:15:00":
                    if trade_id not in alerted_today:
                        send_telegram_alert(f"💸 *INTRADAY EXIT: {t['symbol']} ({t['strategy']})*\nAuto Square-off at Rs {live_price}")
                        alerted_today.add(trade_id)
                    ft.close_trade(trade_id, live_price, "3:15 Auto Square Off")
                    data_changed = True
                    continue

                # Math for Exits
                sl_hit = (trade_type == "LONG" and live_price <= t["stop_loss"]) or \
                         (trade_type == "SHORT" and live_price >= t["stop_loss"])
                
                target_3r = t["entry_price"] + (3 * one_r) if trade_type == "LONG" else t["entry_price"] - (3 * one_r)
                target_2r = t["entry_price"] + (2 * one_r) if trade_type == "LONG" else t["entry_price"] - (2 * one_r)
                
                hit_3r = (trade_type == "LONG" and live_price >= target_3r) or \
                         (trade_type == "SHORT" and live_price <= target_3r)

                # Trap Detection: Drops violently back through entry (Half an R against you)
                trap_hit = (trade_type == "LONG" and live_price < t["entry_price"] - (0.5 * one_r)) or \
                           (trade_type == "SHORT" and live_price > t["entry_price"] + (0.5 * one_r))

                # 1. Stop Loss Hit
                if sl_hit:
                    if trade_id not in alerted_today:
                        send_telegram_alert(f"🔴 *INTRADAY SL HIT: {t['symbol']} ({t['strategy']})*\nExited at Rs {live_price}")
                        alerted_today.add(trade_id)
                    ft.close_trade(trade_id, live_price, "Stop Loss Hit")
                    data_changed = True
                
                # 2. Trap Exit (Emergency Cut)
                elif trap_hit and not t.get("trailed_3r", False):
                    if trade_id not in alerted_today:
                        send_telegram_alert(f"⚠️ *TRAP DETECTED: {t['symbol']} ({t['strategy']})*\nFalse breakout reversed! Emergency exit at Rs {live_price}")
                        alerted_today.add(trade_id)
                    ft.close_trade(trade_id, live_price, "Trap Reversal Exit")
                    data_changed = True

                # 3. Target Reached -> Trail SL
                elif hit_3r and not t.get("trailed_3r", False):
                    t["stop_loss"] = target_2r # Move SL into profit
                    t["trailed_3r"] = True     # Mark as trailed
                    
                    # We only log to Telegram, we let the loop save the updated SL to DB below
                    send_telegram_alert(f"🔥 *3R TARGET REACHED: {t['symbol']} ({t['strategy']})*\nTrailing Stop Loss moved into profit at Rs {target_2r}!")
                    data_changed = True

        if data_changed:
            ft._save(db) # Save any trailed SL updates
            push_to_github()

        time.sleep(20)

if __name__ == "__main__":
    run_intraday_engine()