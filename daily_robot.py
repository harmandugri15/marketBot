import logging
import time
from datetime import datetime, timedelta
from groww_api import GrowwAPI
from scanner import run_scan
import forward_test as ft

# Configure logging for the Cloud Terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] ROBOT: %(message)s")
logger = logging.getLogger(__name__)

def run_daily_automation():
    logger.info("🤖 Waking up Daily Robot...")
    api = GrowwAPI()
    if not api.connected:
        logger.error("❌ Failed to connect to Groww. Aborting.")
        return

    # --- PART 1: AUTO-MANAGER (Manage Existing Portfolio) ---
    logger.info("📊 Checking open Forward Test trades...")
    db = ft._load()
    open_trades = [t for t in db["trades"] if t["status"] in ["WATCHING", "ACTIVE"]]

    for t in open_trades:
        symbol = t["symbol"]
        # Fetch the last 10 days to safely get today's End-of-Day candle
        start_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        raw = api.get_historical_data(symbol, start_date, datetime.now().strftime("%Y-%m-%d"))
        
        if not raw: 
            continue

        # Extract today's price action
        today = raw[-1] 
        today_high = float(today["high"])
        today_low = float(today["low"])

        # Rule 1: Check if a WATCHING stock triggered our Entry Price
        if t["status"] == "WATCHING":
            if today_high >= t["entry_price"]:
                logger.info(f"✅ ENTRY TRIGGERED: {symbol} crossed Rs {t['entry_price']}.")
                ft.mark_entered(t["id"], t["entry_price"])
                t["status"] = "ACTIVE"

        # Rule 2: Check if an ACTIVE stock hit Stop Loss or Target
        if t["status"] == "ACTIVE":
            target_multiplier = 1.06 if t["strategy"] == "MRB" else 1.15
            target_price = t["entry_price"] * target_multiplier

            if today_low <= t["stop_loss"]:
                logger.warning(f"🛑 STOP LOSS HIT: {symbol} dropped to Rs {today_low}. Exiting.")
                ft.close_trade(t["id"], t["stop_loss"], "Stop Loss Hit")
            elif today_high >= target_price:
                logger.info(f"🎯 TARGET HIT: {symbol} surged past Rs {target_price}! Securing profit.")
                ft.close_trade(t["id"], target_price, f"Target Hit ({int((target_multiplier-1)*100)}%)")

    # --- PART 2: THE HUNTER (Scan for new setups) ---
    logger.info("🔍 Running Daily Scanner...")
    signals = run_scan(api, strategy="AUTO")

    # Check the Global Circuit Breaker
    if signals and signals[0].get("market_bearish"):
        logger.warning("🐻 Market is BEARISH. Refusing to take new trades today.")
        return

    # Filter out stocks we are already trading
    existing_symbols = [t["symbol"] for t in db["trades"] if t["status"] in ["WATCHING", "ACTIVE"]]
    fresh_signals = [s for s in signals if s["symbol"] not in existing_symbols]

    if fresh_signals:
        best_signal = fresh_signals[0] # Take the #1 absolute best setup of the day
        logger.info(f"✨ FOUND NEW SETUP: Auto-adding {best_signal['symbol']} to portfolio.")
        ft.add_trade(best_signal)
    else:
        logger.info("📉 No perfect setups found today. Staying safe in cash.")

    logger.info("🤖 Daily routine complete. See you tomorrow.")

if __name__ == "__main__":
    run_daily_automation()