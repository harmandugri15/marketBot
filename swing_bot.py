import os
import logging
import requests
import json
from datetime import datetime, timedelta
import pytz
import pandas as pd
from groww_api import GrowwAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s [SWING]: %(message)s")
logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

SWING_WATCHLIST = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN", "BHARTIARTL", "ITC", "L&T", "BAJFINANCE"]
SWING_CAPITAL = 10000.0  
RISK_PCT = 2.0           
DB_FILE = "data/swing_portfolio.json"

def _load():
    if not os.path.exists("data"): os.makedirs("data")
    if not os.path.exists(DB_FILE): return {"capital": SWING_CAPITAL, "trades": []}
    with open(DB_FILE, "r") as f: return json.load(f)

def _save(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=2)

def send_telegram_alert(msg):
    t, c = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if t and c: requests.post(f"https://api.telegram.org/bot{t}/sendMessage", json={"chat_id": c, "text": msg, "parse_mode": "Markdown"})

def push_to_github():
    os.system('git config --global user.email "bot@marketbot.com"')
    os.system('git config --global user.name "MarketBot Engine"')
    os.system('git add data/swing_portfolio.json')
    os.system('git commit -m "📊 Auto-update Swing Portfolio" || echo "No changes"')
    os.system('git pull origin main --rebase && git push')

def calc_inds(df):
    df = df.copy()
    df["ema10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + (gain / loss)))
    if "volume" in df.columns: df["vol_sma50"] = df["volume"].rolling(50).mean()
    return df

def run_swing_engine():
    api = GrowwAPI()
    now = datetime.now(IST)
    if not ("15:10:00" <= now.strftime("%H:%M:%S") <= "15:30:00"): return

    send_telegram_alert("🔎 *Swing Engine Awake:* Scanning for End-of-Day Setups...")
    db = _load()
    
    realized_pnl = sum(t.get("realized_pnl", 0) for t in db.get("trades", []) if t["status"] == "CLOSED")
    active_trades = [t for t in db.get("trades", []) if t["status"] in ["ACTIVE", "WATCHING"]]
    available_cash = (SWING_CAPITAL + realized_pnl) - sum(t["entry_price"] * t["shares"] for t in active_trades)
    data_changed = False

    # 1. EXITS
    for t in active_trades:
        if t["status"] == "ACTIVE":
            data = api.get_historical_data(t["symbol"], (now - timedelta(days=60)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"))
            if not data: continue
            df = calc_inds(pd.DataFrame(data))
            today = df.iloc[-1]
            
            exit_px, reason = None, ""
            if today["high"] >= t["entry_price"] + (1.5 * t["one_r"]) and t["stop_loss"] < t["entry_price"]:
                t["stop_loss"] = t["entry_price"]
                data_changed = True
                
            if today["low"] <= t["stop_loss"]: exit_px, reason = t["stop_loss"], "Stop Loss Hit"
            elif t["stop_loss"] >= t["entry_price"] and today["close"] < today["ema10"]: exit_px, reason = today["close"], "Trend Broke (EMA10)"
                
            if exit_px:
                t.update({"status": "CLOSED", "exit_price": exit_px, "exit_date": now.strftime("%Y-%m-%d"), "exit_reason": reason})
                t["realized_pnl"] = (exit_px - t["entry_price"]) * t["shares"] - ((exit_px + t["entry_price"]) * t["shares"] * 0.001)
                available_cash += (t["entry_price"] * t["shares"]) + t["realized_pnl"]
                send_telegram_alert(f"💰 *SWING CLOSED: {t['symbol']}*\n{reason}. P&L: Rs {round(t['realized_pnl'], 2)}")
                data_changed = True

    # 2. ENTRIES
    for symbol in SWING_WATCHLIST:
        if symbol in [t["symbol"] for t in active_trades]: continue
        data = api.get_historical_data(symbol, (now - timedelta(days=100)).strftime("%Y-%m-%d"), now.strftime("%Y-%m-%d"))
        if not data: continue
        df = calc_inds(pd.DataFrame(data))
        today = df.iloc[-1]
        
        dist = (today["close"] - today["ema20"]) / today["ema20"]
        if 0 < dist < 0.04 and 40 < today["rsi"] < 65: # Pullback setup
            entry = float(today["close"])
            sl = float(max(min(today["low"] * 0.99, entry * 0.95), entry * 0.92))
            one_r = entry - sl
            
            if one_r > 0 and (one_r/entry*100) <= 8.0:
                shares = min(int(((SWING_CAPITAL + realized_pnl) * (RISK_PCT/100)) / one_r), int(available_cash / entry))
                if shares > 0:
                    db.setdefault("trades", []).append({
                        "id": f"SWING_{symbol}_{now.strftime('%Y%m%d')}",
                        "symbol": symbol, "strategy": "HARMAN1_PULLBACK",
                        "entry_price": round(entry, 2), "stop_loss": round(sl, 2),
                        "one_r": round(one_r, 2), "shares": shares, "status": "ACTIVE",
                        "entry_date": now.strftime("%Y-%m-%d"), "realized_pnl": 0
                    })
                    available_cash -= (entry * shares)
                    data_changed = True
                    send_telegram_alert(f"📈 *NEW SWING: {symbol}*\nBought {shares} shares at Rs {round(entry,2)}")

    if data_changed:
        _save(db)
        push_to_github()

if __name__ == "__main__":
    run_swing_engine()