import os
import logging
import time
import requests
from datetime import datetime, timedelta
from groww_api import GrowwAPI
from scanner import run_scan
import json
import forward_test as ft

# Configure logging for the Cloud Terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] ROBOT: %(message)s")
logger = logging.getLogger(__name__)

def send_telegram_alert(message):
    """Silently broadcasts a markdown-formatted message to your Telegram phone app."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    
    # If the keys aren't set up yet, just gracefully skip the alert
    if not token or not chat_id:
        return
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logger.error(f"Telegram alert failed: {e}")

def run_daily_automation():
    logger.info("🤖 Waking up Daily Robot...")
    send_telegram_alert("☀️ *MarketBot waking up for daily scan...*")
    
    api = GrowwAPI()
    if not api.connected:
        logger.error("❌ Failed to connect to Groww. Aborting.")
        send_telegram_alert("🚨 *CRITICAL ERROR*\nFailed to connect to Groww API. Daily run aborted.")
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
                send_telegram_alert(f"🟢 *TRADE ENTERED*\nBought **{symbol}** at Rs {t['entry_price']}")

        # Rule 2: Check if an ACTIVE stock hit Stop Loss or Target
        if t["status"] == "ACTIVE":
            target_multiplier = 1.06 if t["strategy"] == "MRB" else 1.15
            target_price = round(t["entry_price"] * target_multiplier, 2)

            if today_low <= t["stop_loss"]:
                logger.warning(f"🛑 STOP LOSS HIT: {symbol} dropped to Rs {today_low}. Exiting.")
                ft.close_trade(t["id"], t["stop_loss"], "Stop Loss Hit")
                send_telegram_alert(f"🔴 *STOP LOSS HIT*\nClosed **{symbol}** at Rs {t['stop_loss']}")
                
            elif today_high >= target_price:
                logger.info(f"🎯 TARGET HIT: {symbol} surged past Rs {target_price}! Securing profit.")
                ft.close_trade(t["id"], target_price, f"Target Hit ({int((target_multiplier-1)*100)}%)")
                send_telegram_alert(f"💸 *TARGET HIT*\nClosed **{symbol}** for profit at Rs {target_price}!")

    # --- PART 2: THE HUNTER (Scan for new setups) ---
    logger.info("🔍 Running Daily Scanner...")
    signals = run_scan(api, strategy="AUTO")

    # Check the Global Circuit Breaker
    if signals and signals[0].get("market_bearish"):
        logger.warning("🐻 Market is BEARISH. Refusing to take new trades today.")
        send_telegram_alert("🐻 *MARKET BEARISH*\nCircuit breaker active. No new trades taken today.")
        return

    # Filter out stocks we are already trading
    existing_symbols = [t["symbol"] for t in db["trades"] if t["status"] in ["WATCHING", "ACTIVE"]]
    fresh_signals = [s for s in signals if s["symbol"] not in existing_symbols]

    if fresh_signals:
        best_signal = fresh_signals[0] # Take the #1 absolute best setup of the day
        logger.info(f"✨ FOUND NEW SETUP: Auto-adding {best_signal['symbol']} to portfolio.")
        ft.add_trade(best_signal)
        
        # Notify your phone about the new addition!
        alert_msg = (
            f"🆕 *NEW SETUP FOUND*\n"
            f"Added **{best_signal['symbol']}** to watchlist.\n"
            f"Entry: Rs {best_signal['entry_price']}\n"
            f"Stop Loss: Rs {best_signal['stop_loss']}"
        )
        send_telegram_alert(alert_msg)
    else:
        logger.info("📉 No perfect setups found today. Staying safe in cash.")

    # 👇 YOU ARE MISSING THESE 3 LINES 👇
    import json
    with open("data/summary.json", "w") as f:
        json.dump(ft.get_summary(), f)

    logger.info("🤖 Daily routine complete. See you tomorrow.")

if __name__ == "__main__":
    run_daily_automation()