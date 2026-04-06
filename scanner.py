import os
import json
import logging
import time
import random  # <-- Added for request jitter
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import concurrent.futures

from config import STOCK_UNIVERSE, SIGNALS_DB, get_settings

logger = logging.getLogger(__name__)

def get_market_regime(api):
    """
    Checks Nifty 50 Trend:
    BULL: Above 20 EMA
    CASH: Between 20 and 200 EMA (Dangerous)
    PANIC: Below 200 EMA (Deep Bear - STOP TRADING)
    """
    try:
        raw = api.get_historical_data("^NSEI", from_date=(datetime.now() - timedelta(days=350)).strftime("%Y-%m-%d"), to_date=datetime.now().strftime("%Y-%m-%d"))
        if not raw: return "CASH"
        df = pd.DataFrame(raw).rename(columns={"c": "close"})
        last = df["close"].iloc[-1]
        e20 = df["close"].ewm(span=20, adjust=False).mean().iloc[-1]
        e200 = df["close"].ewm(span=200, adjust=False).mean().iloc[-1]
        if last > e20: return "BULL"
        if last < e200: return "PANIC"
        return "CASH"
    except: return "CASH"

def _build_indicators(df):
    df = df.copy()
    df["ema10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["vol_sma50"] = df["volume"].rolling(50).mean()
    df["daily_ret"] = df["close"].pct_change() * 100
    macd = df["close"].ewm(span=12).mean() - df["close"].ewm(span=26).mean()
    df["macd_hist"] = macd - macd.ewm(span=9).mean()
    df["pivot"] = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + (gain / loss)))
    return df

def run_scan(api, progress_callback=None, strategy="AUTO"):
    settings = get_settings()
    regime = get_market_regime(api)

    # Global Circuit Breaker (Safety Mode)
    if regime == "PANIC" and strategy == "AUTO":
        logger.warning("DEEP BEAR DETECTED: 100% Cash Mode.")
        with open(SIGNALS_DB, "w") as f: json.dump([{"market_bearish": True}], f)
        # return []  <-- Remove the '#' to activate the Emergency Stop for live trading

    signals = []
    total = len(STOCK_UNIVERSE)
    start_date = (datetime.now() - timedelta(days=250)).strftime("%Y-%m-%d")

    # --- THE WORKER FUNCTION ---
    def process_symbol(symbol):
        # 🎓 STAGGERED JITTER: Random sleep between 0.5s and 1.2s
        # This prevents the threads from hitting the API in simultaneous bursts!
        time.sleep(random.uniform(0.5, 1.2)) 
        
        try:
            raw = api.get_historical_data(symbol, from_date=start_date, to_date=datetime.now().strftime("%Y-%m-%d"))
            if not raw or len(raw) < 100: return None
            
            df = _build_indicators(pd.DataFrame(raw).rename(columns={"c":"close","v":"volume","h":"high","l":"low","o":"open"}))
            today, yest = df.iloc[-1], df.iloc[-2]
            
            # Determine active strategy
            active_strat = strategy if strategy != "AUTO" else ("HARMAN1" if regime == "BULL" else "MRB")
            
            setup = None
            
            # Condition 1: EMA Pullback
            dist_to_ema = (today["close"] - today["ema20"]) / today["ema20"]
            is_pullback = 0 < dist_to_ema < 0.04 and 40 < today["rsi"] < 65
            
            # Condition 2: Breakout Surge (Looking at previous 5 days)
            five_day_high = df.iloc[-6:-1]["high"].max()
            is_breakout = today["close"] > five_day_high and today["volume"] > today["vol_sma50"] * 1.5
            
            # Condition 3: Deep Bear Bounce
            is_bear_bounce = today["rsi"] < 35 and today["close"] > yest["high"] and today["volume"] > today["vol_sma50"]

            # Strategy Routing
            if active_strat in ["HARMAN1", "VT"] and regime == "BULL":
                if is_pullback: setup = {"notes": "EMA 20 Pullback", "score": 90}
                elif is_breakout: setup = {"notes": "Volume Breakout Surge", "score": 95}
            elif active_strat in ["MRB", "DEP"]:
                if is_pullback: setup = {"notes": "EMA 20 Pullback", "score": 90}
                elif is_bear_bounce: setup = {"notes": "Deep Bear Bounce", "score": 85}

            if setup and setup["score"] >= settings.get('min_quality', 80):
                # Calculate precise Entry and Stop Loss
                entry = float(today["close"])
                sl = float(max(min(today["low"] * 0.99, entry * 0.95), entry * 0.92))
                one_r = entry - sl
                
                # Risk Management filters
                if one_r > 0 and (one_r / entry * 100) <= settings.get('max_sl_pct', 8.0):
                    shares = int((settings['capital'] * (settings['risk_pct']/100)) / one_r)
                    
                    if shares == 0 and entry <= settings['capital']: shares = 1
                    
                    if shares > 0:
                        return {
                            "strategy": active_strat, 
                            "symbol": symbol, 
                            "entry_price": round(entry, 2), 
                            "stop_loss": round(sl, 2), 
                            "sl_pct": round(one_r/entry*100, 2), 
                            "shares": shares, 
                            "quality_score": setup["score"], 
                            "notes": setup["notes"], 
                            "scan_date": datetime.now().strftime("%Y-%m-%d"),
                            "pullback_pct": round(dist_to_ema * 100, 2),
                            "vol_ratio": round(today["volume"] / today["vol_sma50"], 2),
                            "invested": round(entry * shares, 2)
                        }
        except Exception as e: 
            logger.error(f"Scanner failed to process {symbol}: {e}")
        
        return None

    # --- MULTITHREADING ORCHESTRATOR ---
    processed_count = 0
    # Reduced to 3 workers for maximum API safety
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_symbol = {executor.submit(process_symbol, sym): sym for sym in STOCK_UNIVERSE}
        
        for future in concurrent.futures.as_completed(future_to_symbol):
            sym = future_to_symbol[future]
            processed_count += 1
            
            if progress_callback: 
                progress_callback(processed_count, total, sym)
                
            result = future.result()
            if result:
                signals.append(result)
    
    signals.sort(key=lambda x: x["quality_score"], reverse=True)
    with open(SIGNALS_DB, "w") as f: json.dump(signals, f, indent=2)
    return signals

def load_signals():
    if not os.path.exists(SIGNALS_DB): return []
    try:
        with open(SIGNALS_DB, "r") as f: return json.load(f)
    except: return []