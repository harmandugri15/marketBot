import logging
import json
import os
import time
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from config import STOCK_UNIVERSE, BACKTEST_DB, get_settings

logger = logging.getLogger(__name__)

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer): return int(obj)
        if isinstance(obj, np.floating): return float(obj)
        if isinstance(obj, np.ndarray): return obj.tolist()
        if isinstance(obj, np.bool_): return bool(obj)
        return super(NpEncoder, self).default(obj)

def _format_dataframe(raw_data):
    if not raw_data: return pd.DataFrame()
    df = pd.DataFrame(raw_data)
    if df.empty: return pd.DataFrame()
    
    df.columns = [str(c).lower().strip() for c in df.columns]
    rename_map = {"c": "close", "v": "volume", "h": "high", "l": "low", "o": "open", "timestamp": "date", "datetime": "date"}
    df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns}, inplace=True)
    
    if "date" not in df.columns:
        if not df.empty: df["date"] = df.index
    
    df["date"] = pd.to_datetime(df["date"]).dt.date
    df = df[~df["date"].duplicated(keep='last')] 
    df.set_index("date", inplace=True)
    df.sort_index(inplace=True)
    
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns: df[col] = pd.to_numeric(df[col], errors="coerce")
    df.dropna(subset=["close"], inplace=True)
    return df

def _build_indicators(df):
    df["ema10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + (gain / loss)))
    df["vol_sma50"] = df["volume"].rolling(50).mean()
    return df

def run_backtest(api, start_date, end_date, capital, symbols=None, progress_callback=None, strategy="AUTO"):
    settings = get_settings()
    capital = float(capital or settings['capital'])
    symbols = symbols or STOCK_UNIVERSE
    
    # 1. Fetch Nifty for Market Regime
    raw_nifty = api.get_historical_data("^NSEI", from_date=(datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=365)).strftime("%Y-%m-%d"), to_date=end_date)
    ndf = _format_dataframe(raw_nifty)
    if not ndf.empty:
        ndf["ema20"] = ndf["close"].ewm(span=20).mean()

    running_equity = capital
    all_trades = []
    equity_curve = [{"date": start_date, "equity": capital}]
    market_data = {}

    # 2. Fetch Symbols (With Institutional Throttle)
    for idx, symbol in enumerate(symbols, 1):
        if progress_callback: progress_callback(idx, len(symbols), symbol)
        
        # Give Groww API room to breathe (0.6 seconds per stock)
        time.sleep(2.1) 
        
        try:
            raw = api.get_historical_data(symbol, from_date=(datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=200)).strftime("%Y-%m-%d"), to_date=end_date)
            
            # API Apology Protocol: If Groww blocks us (403), pause for 2 seconds and retry
            if not raw:
                logger.warning(f"Data empty/forbidden for {symbol}. Pausing 2s and retrying...")
                time.sleep(2.0)
                raw = api.get_historical_data(symbol, from_date=(datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=200)).strftime("%Y-%m-%d"), to_date=end_date)

            df = _format_dataframe(raw)
            if len(df) > 50:
                market_data[symbol] = _build_indicators(df)
        except Exception as e: 
            logger.error(f"Failed to process {symbol}: {e}")

    # Synchronize Dates
    all_dates = sorted(list(set().union(*(df.index for df in market_data.values()))))
    dates = [d for d in all_dates if d >= datetime.strptime(start_date, "%Y-%m-%d").date()]
    
    active_trades = []

    for current_date in dates:
        if running_equity < capital * 0.4: break # Account blown shield
        
        nifty_bull = True
        if not ndf.empty and current_date in ndf.index:
            nifty_bull = ndf.loc[current_date]["close"] > ndf.loc[current_date]["ema20"]

        # ── EXIT LOGIC (Dynamic Targets) ──
        for t in active_trades[:]:
            df = market_data.get(t["symbol"])
            if df is None or current_date not in df.index: continue
            today = df.loc[current_date]
            exit_px = None
            
            # Smart Targets: 6% for Bear Market Bounces (MRB), 15% for Bull Runs
            target_multiplier = 1.06 if t["strategy"] == "MRB" else 1.15
            
            # Breakeven Shield
            if not t.get("be_active") and today["high"] >= t["entry_price"] + (1.5 * t["one_r"]):
                t["sl"] = t["entry_price"]
                t["be_active"] = True

            # Evaluate Exits
            if today["low"] <= t["sl"]:
                exit_px, reason = t["sl"], "Stop Loss/BE"
            elif today["high"] >= t["entry_price"] * target_multiplier:
                exit_px, reason = t["entry_price"] * target_multiplier, f"Target Hit ({int((target_multiplier-1)*100)}%)"
            elif t.get("be_active") and today["close"] < today["ema10"]:
                exit_px, reason = today["close"], "Trend Trail Exit"

            if exit_px:
                pnl = (float(exit_px) - t["entry_price"]) * t["shares"]
                t.update({"exit_date": str(current_date), "exit_price": float(exit_px), "exit_reason": reason, "pnl": pnl, "pnl_pct": (pnl/(t["entry_price"]*t["shares"]))*100})
                running_equity += pnl
                equity_curve.append({"date": str(current_date), "equity": round(running_equity, 2)})
                all_trades.append(t); active_trades.remove(t)

        # ── ENTRY LOGIC (Dual Track: Bounce & Surge) ──
        if len(active_trades) < 2:
            for symbol, df in market_data.items():
                if current_date not in df.index: continue
                if any(at["symbol"] == symbol for at in active_trades): continue
                
                loc = df.index.get_loc(current_date)
                if loc < 15: continue
                today, yest = df.iloc[loc], df.iloc[loc-1]
                
                # Determine strategy based on UI setting and Market Regime
                active_strat = strategy if strategy != "AUTO" else ("HARMAN1" if nifty_bull else "MRB")
                
                setup = False
                
                # Condition 1: EMA Pullback
                dist_to_ema = (today["close"] - today["ema20"]) / today["ema20"]
                is_pullback = 0 < dist_to_ema < 0.04 and 40 < today["rsi"] < 65
                
                # Condition 2: Breakout Surge
                five_day_high = df.iloc[loc-5:loc]["high"].max()
                is_breakout = today["close"] > five_day_high and today["volume"] > today["vol_sma50"] * 1.5
                
                # Condition 3: Deep Bear Bounce
                is_bear_bounce = today["rsi"] < 35 and today["close"] > yest["high"] and today["volume"] > today["vol_sma50"]

                if active_strat in ["HARMAN1", "VT"] and nifty_bull:
                    if is_pullback or is_breakout: setup = True
                elif active_strat in ["MRB", "DEP"]:
                    if is_pullback or is_bear_bounce: setup = True

                if setup:
                    entry = float(today["close"])
                    # Adaptive SL: 1% below today's low, capped at 5% risk
                    sl = float(max(min(today["low"] * 0.99, entry * 0.95), entry * 0.92))
                    one_r = entry - sl
                    
                    if one_r > 0 and (one_r/entry*100) <= 8.0:
                        shares = int((running_equity * 0.45) / entry) # 45% position size per trade
                        if shares > 0:
                            active_trades.append({
                                "symbol": symbol, "strategy": active_strat, "entry_date": str(current_date), 
                                "entry_price": round(entry,2), "sl": round(sl,2), "shares": shares, 
                                "one_r": one_r, "be_active": False
                            })
                            break # Max 1 entry per day to avoid over-exposure

    # Clean up open trades at end of period
    for t in active_trades:
        df = market_data.get(t["symbol"])
        if df is not None and not df.empty:
            last_px = df.iloc[-1]["close"]
            pnl = (last_px - t["entry_price"]) * t["shares"]
            t.update({"exit_date": str(dates[-1]), "exit_price": last_px, "exit_reason": "End of Test", "pnl": pnl, "pnl_pct": (pnl/(t["entry_price"]*t["shares"]))*100})
            running_equity += pnl
            all_trades.append(t)

    wins = [t for t in all_trades if t["pnl"] > 0]
    losses = [t for t in all_trades if t["pnl"] <= 0]
    
    # Calculate Max Drawdown
    max_dd = 0; peak = capital
    for point in equity_curve:
        if point["equity"] > peak: peak = point["equity"]
        dd = ((peak - point["equity"]) / peak) * 100
        if dd > max_dd: max_dd = dd

    results = {
        "start_date": start_date, "end_date": end_date, "starting_capital": capital, "strategy_run": strategy,
        "metrics": {
            "final_equity": round(running_equity, 2),
            "total_return_pct": round(((running_equity - capital) / capital) * 100, 2) if capital else 0,
            "total_trades": len(all_trades), "winning_trades": len(wins), "losing_trades": len(losses),
            "win_rate": round(len(wins) / len(all_trades) * 100, 1) if all_trades else 0,
            "profit_factor": round(sum(t["pnl"] for t in wins) / abs(sum(t["pnl"] for t in losses)), 2) if losses else 999,
            "avg_win_pct": round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0,
            "avg_loss_pct": round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0,
            "max_drawdown_pct": round(max_dd, 2)
        },
        "trades": sorted(all_trades, key=lambda x: x["entry_date"]),
        "equity_curve": equity_curve
    }
    with open(BACKTEST_DB, "w") as f: json.dump(results, f, indent=2, cls=NpEncoder)
    return results

def load_backtest_results():
    if not os.path.exists(BACKTEST_DB): return {}
    try:
        with open(BACKTEST_DB, "r") as f: return json.load(f)
    except: return {}