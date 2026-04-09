import os
import time
import logging
import requests
from datetime import datetime
import pytz
from groww_api import GrowwAPI
import forward_test as ft

logging.basicConfig(level=logging.INFO, format="%(asctime)s [INTRADAY]: %(message)s")
logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

# ==========================================
# TELEGRAM NOTIFICATION FUNCTION
# ==========================================
def send_telegram_alert(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
            requests.post(url, json=payload)
        except Exception as e:
            logger.error(f"Telegram failed: {e}")

# ==========================================
# GITHUB SYNC FUNCTION (This was missing!)
# ==========================================
def push_to_github():
    """Commits the updated JSON file to GitHub so the public website updates."""
    try:
        os.system('git config --global user.email "bot@marketbot.com"')
        os.system('git config --global user.name "MarketBot Engine"')
        os.system('git add data/forward_test.json')
        os.system('git commit -m "🤖 Auto-update trades" || echo "No changes to commit"')
        
        # 👇 THIS LINE MUST BE IN BOTH PYTHON FILES TO PREVENT CRASHES
        os.system('git pull origin main --rebase')
        
        os.system('git push')
        logger.info("☁️ Pushed live trade updates to GitHub Pages!")
    except Exception as e:
        logger.error(f"Failed to push to GitHub: {e}")

# ==========================================
# MAIN TRADING ENGINE
# ==========================================
def run_intraday_engine():
    send_telegram_alert("⏱️ *Intraday Bot Awakening...* Monitoring 9:20 AM setups.")
    
    api = GrowwAPI()
    if not api.connected: 
        logger.error("❌ Groww API not connected.")
        return

    while True:
        now = datetime.now(IST)
        current_time = now.strftime("%H:%M:%S")
        
        # Shut down intraday engine at 3:20 PM
        if current_time > "15:20:00":
            push_to_github()
            break

        db = ft._load()
        # Filter for only Intraday strategies
        trades = [t for t in db.get("trades", []) if "INTRADAY" in t["strategy"] and t["status"] != "CLOSED"]
        data_changed = False
        
        for t in trades:
            live_price = api.get_live_price(t["symbol"])
            if not live_price: continue

            # 1. WATCHING -> ACTIVE
            if t["status"] == "WATCHING" and live_price >= t["entry_price"]:
                send_telegram_alert(f"🚀 *INTRADAY ENTRY:* {t['symbol']} hit {live_price}!")
                ft.mark_entered(t["id"], live_price)
                data_changed = True
            
            # 2. ACTIVE -> CLOSED (Intraday Auto Square Off)
            elif t["status"] == "ACTIVE":
                if current_time >= "15:15:00":
                    send_telegram_alert(f"💸 *INTRADAY EXIT:* Auto Square-off for {t['symbol']} at {live_price}")
                    ft.close_trade(t["id"], live_price, "3:15 Auto Square Off")
                    data_changed = True
                elif live_price <= t["stop_loss"]:
                    send_telegram_alert(f"🔴 *INTRADAY SL HIT:* {t['symbol']} exited at {live_price}")
                    ft.close_trade(t["id"], live_price, "Stop Loss Hit")
                    data_changed = True

        # 👇 If trades were entered or exited, push the changes to the website!
        if data_changed:
            push_to_github()

        time.sleep(20) # Fast polling for intraday

if __name__ == "__main__":
    run_intraday_engine()