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
    
    # =========================================================================
    # ⏱️ SPECIAL INTRADAY ENGINE (LONG ONLY + TIME FILTER)
    # =========================================================================
    if strategy == "INTRADAY_ORB":
        logger.info("Running Phase 1: Scanning for setups...")
        
        running_equity = capital
        all_trades = []
        equity_curve = [{"date": start_date, "equity": capital}]
        potential_trades = []
        
        for idx, symbol in enumerate(symbols, 1):
            if progress_callback: progress_callback(idx, len(symbols), symbol)
            time.sleep(1.5)
            
            try:
                raw_data = api.get_historical_intraday_data(symbol, start_date, end_date)
                if not raw_data: continue
                
                df = pd.DataFrame(raw_data)
                df['ema7'] = df['close'].ewm(span=7, adjust=False).mean()
                df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
                
                for date, daily_df in df.groupby('date'):
                    if len(daily_df) < 5: continue
                    daily_df = daily_df.copy()
                    daily_df['vwap'] = (daily_df['typical_price'] * daily_df['volume']).cumsum() / daily_df['volume'].cumsum()
                    
                    morning_candles = daily_df.iloc[0:3]
                    range_high = float(morning_candles['high'].max())
                    range_low = float(morning_candles['low'].min())
                    third_candle = morning_candles.iloc[-1]
                    c3_close, vwap, ema7 = float(third_candle['close']), float(third_candle['vwap']), float(third_candle['ema7'])
                    
                    buffer = range_high * 0.001 
                    setup_type = None
                    trigger = target = sl = 0
                    
                    if c3_close > vwap and c3_close > ema7:
                        setup_type = "LONG"
                        trigger = range_high + buffer
                        sl = range_low - buffer
                        target = trigger + (1.5 * (trigger - sl)) 

                    if setup_type:
                        trade_active = False
                        entry_price = one_r_amount = 0
                        entry_time = ""
                        
                        for _, candle in daily_df.iloc[3:].iterrows():
                            c_high, c_low, c_close = float(candle['high']), float(candle['low']), float(candle['close'])
                            c_time = str(candle['time'])
                            
                            if not trade_active:
                                # 👇 THE TIME FIX: DO NOT take new trades after 2:45 PM
                                if c_time >= "14:45:00":
                                    continue 
                                    
                                if c_high >= trigger:
                                    trade_active = True
                                    entry_price = trigger
                                    one_r_amount = abs(trigger - sl)
                                    entry_time = c_time
                                    
                            if trade_active:
                                exit_px = None
                                reason = ""
                                
                                if c_high >= (entry_price + one_r_amount) and sl < entry_price: 
                                    sl = entry_price 
                                    
                                if c_low <= sl: 
                                    exit_px = sl
                                    reason = "Stop Loss Hit" if sl < entry_price else "Breakeven Stop"
                                elif c_high >= target: 
                                    exit_px, reason = target, "Target Hit (1.5R)"
                                
                                if not exit_px and c_time >= "15:15:00":
                                    exit_px, reason = c_close, "3:15 Auto Square Off"
                                    
                                if exit_px:
                                    potential_trades.append({
                                        "symbol": symbol, "type": setup_type, "date": str(date),
                                        "entry_time": entry_time, "exit_time": c_time,
                                        "entry_price": entry_price, "exit_price": exit_px,
                                        "sl": sl, "reason": reason
                                    })
                                    break 

            except Exception as e:
                logger.error(f"Intraday BT failed for {symbol}: {e}")

        logger.info("Running Phase 2: Simulating unified global wallet...")
        dates = sorted(list(set([t['date'] for t in potential_trades])))
        
        for date in dates:
            day_trades = [t for t in potential_trades if t['date'] == date]
            day_trades.sort(key=lambda x: x['entry_time']) 
            
            daily_bp = running_equity  
            active_day_positions = []
            
            for trade in day_trades:
                for active in active_day_positions[:]:
                    if active['exit_time'] <= trade['entry_time']:
                        daily_bp += (active['margin_used'] + active['pnl']) 
                        running_equity += active['pnl']   
                        all_trades.append(active['record'])
                        active_day_positions.remove(active)
                
                risk_amt = running_equity * (settings.get('risk_pct', 2.0) / 100)
                one_r = abs(trade['entry_price'] - trade['sl'])
                desired_shares = int(risk_amt / one_r) if one_r > 0 else 1
                
                max_affordable = int(daily_bp / trade['entry_price']) if trade['entry_price'] > 0 else 0
                actual_shares = min(desired_shares, max_affordable)
                
                if actual_shares > 0:
                    margin_used = actual_shares * trade['entry_price']
                    daily_bp -= margin_used 
                    
                    pnl = (trade['exit_price'] - trade['entry_price']) * actual_shares
                    
                    # 👇 TIMESTAMP FIX: Attaching the exact time to the date so you can see it in the UI!
                    record = {
                        "symbol": trade['symbol'], 
                        "strategy": "INTRADAY (LONG)", 
                        "entry_date": f"{trade['date']} {trade['entry_time'][:5]}", 
                        "exit_date": f"{trade['date']} {trade['exit_time'][:5]}", 
                        "entry_price": round(trade['entry_price'],2), "exit_price": round(trade['exit_price'],2), 
                        "shares": actual_shares, "pnl": round(pnl,2), 
                        "pnl_pct": round((pnl/(trade['entry_price']*actual_shares))*100, 2) if trade['entry_price'] > 0 else 0,
                        "exit_reason": trade['reason']
                    }
                    
                    active_day_positions.append({
                        'exit_time': trade['exit_time'], 'margin_used': margin_used,
                        'pnl': pnl, 'record': record
                    })
            
            for active in active_day_positions:
                running_equity += active['pnl']
                all_trades.append(active['record'])
                
            if equity_curve[-1]["date"] != date:
                equity_curve.append({"date": date, "equity": round(running_equity, 2)})
            else:
                equity_curve[-1]["equity"] = round(running_equity, 2)

    # =========================================================================
    # 🌊 STANDARD SWING ENGINE 
    # =========================================================================
    else:
        raw_nifty = api.get_historical_data("^NSEI", from_date=(datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=365)).strftime("%Y-%m-%d"), to_date=end_date)
        ndf = _format_dataframe(raw_nifty)
        if not ndf.empty:
            ndf["ema20"] = ndf["close"].ewm(span=20).mean()

        running_equity = capital
        all_trades = []
        equity_curve = [{"date": start_date, "equity": capital}]
        market_data = {}

        for idx, symbol in enumerate(symbols, 1):
            if progress_callback: progress_callback(idx, len(symbols), symbol)
            time.sleep(2.1) 
            
            try:
                raw = api.get_historical_data(symbol, from_date=(datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=200)).strftime("%Y-%m-%d"), to_date=end_date)
                if not raw:
                    time.sleep(2.0)
                    raw = api.get_historical_data(symbol, from_date=(datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=200)).strftime("%Y-%m-%d"), to_date=end_date)

                df = _format_dataframe(raw)
                if len(df) > 50:
                    market_data[symbol] = _build_indicators(df)
            except Exception as e: pass

        all_dates = sorted(list(set().union(*(df.index for df in market_data.values()))))
        dates = [d for d in all_dates if d >= datetime.strptime(start_date, "%Y-%m-%d").date()]
        active_trades = []

        for current_date in dates:
            if running_equity < capital * 0.4: break 
            
            nifty_bull = True
            if not ndf.empty and current_date in ndf.index:
                nifty_bull = ndf.loc[current_date]["close"] > ndf.loc[current_date]["ema20"]

            for t in active_trades[:]:
                df = market_data.get(t["symbol"])
                if df is None or current_date not in df.index: continue
                today = df.loc[current_date]
                exit_px = None
                target_multiplier = 1.06 if t["strategy"] == "MRB" else 1.15
                
                if not t.get("be_active") and today["high"] >= t["entry_price"] + (1.5 * t["one_r"]):
                    t["sl"] = t["entry_price"]
                    t["be_active"] = True

                if today["low"] <= t["sl"]: exit_px, reason = t["sl"], "Stop Loss/BE"
                elif today["high"] >= t["entry_price"] * target_multiplier: exit_px, reason = t["entry_price"] * target_multiplier, f"Target Hit"
                elif t.get("be_active") and today["close"] < today["ema10"]: exit_px, reason = today["close"], "Trend Trail Exit"

                if exit_px:
                    pnl = (float(exit_px) - t["entry_price"]) * t["shares"]
                    t.update({"exit_date": str(current_date), "exit_price": float(exit_px), "exit_reason": reason, "pnl": pnl, "pnl_pct": (pnl/(t["entry_price"]*t["shares"]))*100})
                    running_equity += pnl
                    equity_curve.append({"date": str(current_date), "equity": round(running_equity, 2)})
                    all_trades.append(t)
                    active_trades.remove(t)

            if len(active_trades) < 2:
                for symbol, df in market_data.items():
                    if current_date not in df.index: continue
                    if any(at["symbol"] == symbol for at in active_trades): continue
                    
                    loc = df.index.get_loc(current_date)
                    if loc < 15: continue
                    today, yest = df.iloc[loc], df.iloc[loc-1]
                    
                    active_strat = strategy if strategy != "AUTO" else ("HARMAN1" if nifty_bull else "MRB")
                    setup = False
                    
                    dist_to_ema = (today["close"] - today["ema20"]) / today["ema20"]
                    is_pullback = 0 < dist_to_ema < 0.04 and 40 < today["rsi"] < 65
                    five_day_high = df.iloc[loc-5:loc]["high"].max()
                    is_breakout = today["close"] > five_day_high and today["volume"] > today["vol_sma50"] * 1.5
                    is_bear_bounce = today["rsi"] < 35 and today["close"] > yest["high"] and today["volume"] > today["vol_sma50"]

                    if active_strat in ["HARMAN1", "VT"] and nifty_bull:
                        if is_pullback or is_breakout: setup = True
                    elif active_strat in ["MRB", "DEP"]:
                        if is_pullback or is_bear_bounce: setup = True

                    if setup:
                        entry = float(today["close"])
                        sl = float(max(min(today["low"] * 0.99, entry * 0.95), entry * 0.92))
                        one_r = entry - sl
                        if one_r > 0 and (one_r/entry*100) <= 8.0:
                            risk_shares = int((running_equity * (settings.get('risk_pct', 2.0)/100)) / one_r)
                            
                            cash_tied_up = sum([at["shares"] * at["entry_price"] for at in active_trades])
                            available_cash = running_equity - cash_tied_up
                            
                            max_shares = int(available_cash / entry)
                            shares = min(risk_shares, max_shares)
                            
                            if shares > 0:
                                active_trades.append({
                                    "symbol": symbol, "strategy": active_strat, "entry_date": str(current_date), 
                                    "entry_price": round(entry,2), "sl": round(sl,2), "shares": shares, 
                                    "one_r": one_r, "be_active": False
                                })
                                break

        for t in active_trades:
            df = market_data.get(t["symbol"])
            if df is not None and not df.empty:
                last_px = df.iloc[-1]["close"]
                pnl = (last_px - t["entry_price"]) * t["shares"]
                t.update({"exit_date": str(dates[-1]), "exit_price": last_px, "exit_reason": "End of Test", "pnl": pnl, "pnl_pct": (pnl/(t["entry_price"]*t["shares"]))*100})
                running_equity += pnl
                all_trades.append(t)

    # =========================================================================
    # 📊 RESULTS COMPILATION (Universal)
    # =========================================================================
    wins = [t for t in all_trades if t["pnl"] > 0]
    losses = [t for t in all_trades if t["pnl"] <= 0]
    
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