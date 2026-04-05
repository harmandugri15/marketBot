import os
import json
import logging
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
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

    if regime == "PANIC" and strategy == "AUTO":
        logger.warning("DEEP BEAR DETECTED: 100% Cash Mode.")
        with open(SIGNALS_DB, "w") as f: json.dump([{"market_bearish": True}], f)
        #return []

    signals = []
    total = len(STOCK_UNIVERSE)
    start_date = (datetime.now() - timedelta(days=250)).strftime("%Y-%m-%d")

    for i, symbol in enumerate(STOCK_UNIVERSE, 1):
        if progress_callback: progress_callback(i, total, symbol)
        try:
            raw = api.get_historical_data(symbol, from_date=start_date, to_date=datetime.now().strftime("%Y-%m-%d"))
            if not raw or len(raw) < 100: continue
            df = _build_indicators(pd.DataFrame(raw).rename(columns={"c":"close","v":"volume","h":"high","l":"low","o":"open"}))
            today, yest = df.iloc[-1], df.iloc[-2]
            active_strat = strategy if strategy != "AUTO" else ("HARMAN1" if regime == "BULL" else "MRB")
            
            setup = None
            if active_strat == "HARMAN1":
                exp = any(df['daily_ret'].iloc[j] >= settings['expansion_pct'] and df['volume'].iloc[j] >= df['vol_sma50'].iloc[j]*settings['vol_mult'] for j in range(len(df)-16, len(df)-1))
                if exp and today["volume"] <= today["vol_sma50"] * 1.5 and today["close"] > today["ema20"] and today["macd_hist"] > yest["macd_hist"]:
                    setup = {"notes": "Harman1: Expansion + Momentum", "score": 95}
            elif active_strat == "MRB":
                if (yest["rsi"] < settings['rsi_oversold'] or today["rsi"] < settings['rsi_oversold']) and today["close"] > yest["high"]:
                    if today["volume"] > today["vol_sma50"] * 1.2: # Volume confirmation
                        setup = {"notes": "MRB: Volume Confirmed Bounce", "score": 90}

            if setup and setup["score"] >= settings['min_quality']:
                entry, sl = round(today["high"] + 0.05, 2), round(min(today["low"], yest["low"]) - 0.05, 2)
                one_r = entry - sl
                if (one_r / entry * 100) <= settings['max_sl_pct']:
                    shares = int((settings['capital'] * (settings['risk_pct']/100)) / one_r) if one_r > 0 else 0
                    if shares == 0 and entry <= settings['capital']: shares = 1
                    if shares > 0:
                        signals.append({"strategy": active_strat, "symbol": symbol, "entry_price": entry, "stop_loss": sl, "sl_pct": round(one_r/entry*100,2), "shares": shares, "quality_score": setup["score"], "notes": setup["notes"], "scan_date": datetime.now().strftime("%Y-%m-%d")})
        except: continue
    
    signals.sort(key=lambda x: x["quality_score"], reverse=True)
    with open(SIGNALS_DB, "w") as f: json.dump(signals, f, indent=2)
    return signals

def load_signals():
    if not os.path.exists(SIGNALS_DB): return []
    try:
        with open(SIGNALS_DB, "r") as f: return json.load(f)
    except: return []