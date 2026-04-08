import time
import logging
import os
from datetime import datetime
import pytz
from groww_api import GrowwAPI
import forward_test as ft

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] PAPER: %(message)s")
logger = logging.getLogger(__name__)
IST = pytz.timezone('Asia/Kolkata')

def push_to_github():
    """Commits the updated JSON file to GitHub so the public website updates."""
    try:
        os.system('git config --global user.email "bot@marketbot.com"')
        os.system('git config --global user.name "MarketBot Engine"')
        os.system('git add data/forward_test.json')
        os.system('git commit -m "🤖 Auto-update paper trades"')
        
        # 👇 THIS IS THE MAGIC LINE: Download any laptop changes before pushing!
        os.system('git pull origin main --rebase')
        
        os.system('git push')
        logger.info("☁️ Pushed live trade updates to GitHub Pages!")
    except Exception as e:
        logger.error(f"Failed to push to GitHub: {e}")

def run_paper_trading():
    logger.info("🌅 Paper Trading Engine Booting Up...")
    api = GrowwAPI()
    
    if not api.connected:
        logger.error("❌ Groww API not connected. Exiting.")
        return

    while True:
        now = datetime.now(IST)
        current_time = now.strftime("%H:%M:%S")
        
        if current_time > "15:30:00":
            logger.info("🕒 Market Closed. Shutting down paper engine.")
            push_to_github() # Final sync for the day
            break

        db = ft._load()
        trades = db.get("trades", [])
        data_changed = False

        for t in trades:
            if t["status"] == "CLOSED": 
                continue

            live_price = api.get_live_price(t["symbol"])
            if not live_price: 
                continue

            # 1. WATCHING -> ACTIVE (Entry Logic)
            if t["status"] == "WATCHING":
                # Assuming standard LONG breakout logic for paper trades
                if live_price >= t["entry_price"]:
                    logger.info(f"🚀 {t['symbol']} crossed entry! Moving to ACTIVE.")
                    ft.mark_entered(t["id"], live_price)
                    data_changed = True

            # 2. ACTIVE -> CLOSED (Exit Logic)
            elif t["status"] == "ACTIVE":
                sl = t["stop_loss"]
                # Rough 1.5R Target calculation based on SL
                risk = t["entry_price"] - sl
                target = t["entry_price"] + (1.5 * risk) if risk > 0 else 0
                
                exit_px = None
                reason = ""

                if live_price <= sl:
                    exit_px, reason = live_price, "Stop Loss Hit"
                elif target > 0 and live_price >= target:
                    exit_px, reason = live_price, "Target Hit (1.5R)"
                elif current_time >= "15:15:00" and "INTRADAY" in t["strategy"]:
                    exit_px, reason = live_price, "3:15 Auto Square Off"

                if exit_px:
                    logger.info(f"💸 Closing {t['symbol']} at {exit_px} ({reason})")
                    ft.close_trade(t["id"], exit_px, reason)
                    data_changed = True

        if data_changed:
            push_to_github()

        # Sleep for 30 seconds before checking prices again to respect API limits
        time.sleep(30)

if __name__ == "__main__":
    run_paper_trading()