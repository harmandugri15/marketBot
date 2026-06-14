"""
services/backtest_service.py
-----------------------------
Backtesting engine for VCP, swing pullback (HARMAN1_PULLBACK), and intraday (VWAP_RUNNER) strategies.
Restructured for DB persistence, multi-strategy routing, and proper isolation of simulation logic.
"""

import logging
import time
from datetime import datetime, timedelta, date
from typing import Callable, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from config import get_settings, STOCK_UNIVERSE
from core.indicators import detect_vcp, detect_swing_pullback, detect_vwap_bounce, add_emas
from core.groww_client import GrowwClient
from models.user import User
from models.backtest_result import BacktestResult
from schemas.backtest import BacktestRequest

logger = logging.getLogger(__name__)
settings = get_settings()


def _build_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ema10"] = df["close"].ewm(span=10, adjust=False).mean()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    delta = df["close"].diff()
    gain  = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss  = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    df["rsi"] = 100 - (100 / (1 + (gain / loss.replace(0, np.nan))))
    if "volume" in df.columns:
        df["vol_sma50"] = df["volume"].rolling(50).mean()
    return df


def _simulate_vcp_trades(
    df: pd.DataFrame,
    symbol: str,
    capital: float,
    risk_pct: float,
    max_sl_pct: float,
) -> list[dict]:
    """
    Walk-forward VCP simulation on daily OHLCV.
    Returns list of trade dicts.
    """
    trades = []
    in_trade = False
    entry = sl = target = qty = 0

    for i in range(60, len(df)):
        window = df.iloc[:i]
        today  = df.iloc[i]

        if not in_trade:
            result = detect_vcp(window)
            if result["passed"] and result["score"] >= settings.min_quality:
                entry  = result["entry"]
                sl     = result["stop_loss"]
                target = result["target"] or entry * 1.25
                risk   = entry - sl
                if risk <= 0:
                    continue
                qty = int((capital * risk_pct / 100) / risk)
                if qty < 1:
                    continue
                in_trade   = True
                entry_date = df.index[i]
        else:
            low  = today["low"]
            high = today["high"]

            if low <= sl:
                pnl = (sl - entry) * qty
                trades.append({
                    "symbol":      symbol,
                    "entry":       entry,
                    "exit":        sl,
                    "qty":         qty,
                    "pnl":         round(pnl, 2),
                    "pnl_pct":     round((sl - entry) / entry * 100, 2) if entry > 0 else 0,
                    "exit_reason": "SL_HIT",
                    "entry_date":  str(entry_date),
                    "exit_date":   str(df.index[i]),
                })
                in_trade = False
            elif high >= target:
                pnl = (target - entry) * qty
                trades.append({
                    "symbol":      symbol,
                    "entry":       entry,
                    "exit":        target,
                    "qty":         qty,
                    "pnl":         round(pnl, 2),
                    "pnl_pct":     round((target - entry) / entry * 100, 2) if entry > 0 else 0,
                    "exit_reason": "TARGET_HIT",
                    "entry_date":  str(entry_date),
                    "exit_date":   str(df.index[i]),
                })
                in_trade = False

    return trades


def _simulate_swing_trades(
    market_data: dict[str, pd.DataFrame],
    start_date: date,
    end_date: date,
    capital: float,
    risk_pct: float,
) -> list[dict]:
    """
    Portfolio-level backtest for Swing Pullback (HARMAN1_PULLBACK) strategy
    respecting capital allocation and a maximum of 2 concurrent trades.
    """
    running_equity = capital
    active_trades = []
    all_trades = []

    all_dates = sorted(list(set().union(*(df.index for df in market_data.values()))))
    dates = [d for d in all_dates if d >= start_date and d <= end_date]

    for current_date in dates:
        if running_equity < capital * 0.4:
            break

        # Check exits
        for t in active_trades[:]:
            df = market_data.get(t["symbol"])
            if df is None or current_date not in df.index:
                continue
            today = df.loc[current_date]
            exit_px = None

            target_px = t["target"]
            sl_px = t["sl"]

            # Break Even Trail: move stop loss to entry if 1.5R profit hit
            if not t.get("be_active") and today["high"] >= t["entry_price"] + (1.5 * t["one_r"]):
                t["sl"] = t["entry_price"]
                t["be_active"] = True
                sl_px = t["entry_price"]

            if today["low"] <= sl_px:
                exit_px = sl_px
                reason = "Stop Loss/BE"
            elif today["high"] >= target_px:
                exit_px = target_px
                reason = "Target Hit"
            elif t.get("be_active") and today["close"] < today["ema10"]:
                exit_px = today["close"]
                reason = "Trend Trail Exit"

            if exit_px is not None:
                pnl = (float(exit_px) - t["entry_price"]) * t["shares"]
                # turnover charges (fees & taxes) around 0.1% total turnover
                turnover = (t["entry_price"] + float(exit_px)) * t["shares"]
                fees = turnover * 0.001
                pnl = pnl - fees

                t.update({
                    "exit_date":   str(current_date),
                    "exit":        float(exit_px),
                    "exit_reason": reason,
                    "pnl":         round(pnl, 2),
                    "pnl_pct":     round((pnl / (t["entry_price"] * t["shares"])) * 100, 2) if t["entry_price"] > 0 else 0,
                    "qty":         t["shares"],
                })
                running_equity += pnl
                all_trades.append(t)
                active_trades.remove(t)

        # Scan for new setups
        if len(active_trades) < 2:
            for symbol, df in market_data.items():
                if current_date not in df.index:
                    continue
                if any(at["symbol"] == symbol for at in active_trades):
                    continue

                loc = df.index.get_loc(current_date)
                if loc < 20:
                    continue

                window = df.iloc[:loc+1]
                result = detect_swing_pullback(window)
                if result["passed"]:
                    entry = result["entry"]
                    sl = result["stop_loss"]
                    target = result["target"]
                    one_r = entry - sl

                    risk_shares = int((running_equity * (risk_pct / 100)) / one_r) if one_r > 0 else 0
                    cash_tied_up = sum([at["shares"] * at["entry_price"] for at in active_trades])
                    available_cash = running_equity - cash_tied_up
                    max_shares = int(available_cash / entry) if entry > 0 else 0
                    shares = min(risk_shares, max_shares)

                    if shares > 0:
                        active_trades.append({
                            "symbol":      symbol,
                            "strategy":    "HARMAN1_PULLBACK",
                            "entry_date":  str(current_date),
                            "entry_price": round(entry, 2),
                            "entry":       round(entry, 2),
                            "sl":          round(sl, 2),
                            "target":      round(target, 2),
                            "shares":      shares,
                            "qty":         shares,
                            "one_r":       one_r,
                            "be_active":   False,
                        })
                        if len(active_trades) >= 2:
                            break

    # EOD cleanup
    for t in active_trades:
        df = market_data.get(t["symbol"])
        if df is not None and not df.empty:
            last_px = df.iloc[-1]["close"]
            pnl = (last_px - t["entry_price"]) * t["shares"]
            turnover = (t["entry_price"] + last_px) * t["shares"]
            fees = turnover * 0.001
            pnl = pnl - fees
            t.update({
                "exit_date":   str(end_date),
                "exit":        float(last_px),
                "exit_reason": "End of Test",
                "pnl":         round(pnl, 2),
                "pnl_pct":     round((pnl / (t["entry_price"] * t["shares"])) * 100, 2) if t["entry_price"] > 0 else 0,
                "qty":         t["shares"],
            })
            running_equity += pnl
            all_trades.append(t)

    return all_trades


def _simulate_intraday_trades(
    market_data: dict[str, pd.DataFrame],
    capital: float,
    risk_pct: float,
) -> list[dict]:
    """
    Portfolio-level backtest for Intraday VWAP Bounce (VWAP_RUNNER) strategy
    simulating a 5x leveraged MIS account wallet.
    """
    potential_trades = []

    for symbol, df in market_data.items():
        for date_val, daily_df in df.groupby("date"):
            if len(daily_df) < 5:
                continue

            daily_df = daily_df.copy()
            # Calculate typical price and VWAP
            typical_price = (daily_df["high"] + daily_df["low"] + daily_df["close"]) / 3
            daily_df["vwap"] = (typical_price * daily_df["volume"]).cumsum() / daily_df["volume"].cumsum()

            day_open = float(daily_df.iloc[0]["open"])
            trade_active = False
            entry_price = 0.0
            sl = 0.0
            one_r_amount = 0.0
            entry_time = ""

            for i in range(4, len(daily_df)):
                current_candle = daily_df.iloc[i]
                prev_candle = daily_df.iloc[i-1]
                c_time = str(current_candle["time"])

                c_high = float(current_candle["high"])
                c_low = float(current_candle["low"])
                c_close = float(current_candle["close"])
                c_open = float(current_candle["open"])
                vwap = float(current_candle["vwap"])

                # --- EXIT & TRAILING LOGIC ---
                if trade_active:
                    exit_px = None
                    reason = ""

                    # Trailing Stop Math
                    # Move to break even if 2R profit hit
                    if c_high >= entry_price + (2 * one_r_amount) and sl < entry_price:
                        sl = entry_price

                    # Trail stop loss underneath rising VWAP (if in profit)
                    if sl >= entry_price and vwap > sl:
                        sl = vwap * 0.998

                    # Exits
                    if c_low <= sl:
                        exit_px = sl
                        reason = "Trailed Profit Blocked" if sl >= entry_price else "Stop Loss Hit"
                    elif c_time >= "14:45:00":
                        exit_px = c_close
                        reason = "End of Day Square Off"

                    if exit_px is not None:
                        potential_trades.append({
                            "symbol":      symbol,
                            "type":        "LONG",
                            "date":        str(date_val),
                            "entry_time":  entry_time,
                            "exit_time":   c_time,
                            "entry_price": entry_price,
                            "exit_price":  exit_px,
                            "sl":          sl,
                            "reason":      reason,
                        })
                        trade_active = False

                # --- ENTRY LOGIC (THE BOUNCE) ---
                if not trade_active and "09:35:00" <= c_time <= "11:30:00":
                    distance_to_vwap = abs(prev_candle["low"] - vwap) / vwap
                    if c_close > day_open and distance_to_vwap < 0.002:
                        if c_close > c_open:  # Green Confirmation
                            entry = c_close
                            potential_sl = vwap * 0.998
                            one_r = entry - potential_sl
                            if one_r > 0 and (one_r / entry * 100) < 1.5:
                                trade_active = True
                                entry_price = entry
                                sl = potential_sl
                                one_r_amount = one_r
                                entry_time = c_time

    # Simulate MIS Leverage sizing daily
    all_trades = []
    dates = sorted(list(set([t["date"] for t in potential_trades])))
    MIS_LEVERAGE = 5.0
    running_equity = capital

    for date_val in dates:
        day_trades = [t for t in potential_trades if t["date"] == date_val]
        day_trades.sort(key=lambda x: x["entry_time"])

        daily_bp = running_equity
        active_day_positions = []

        for trade in day_trades:
            # Release expired positions
            for active in active_day_positions[:]:
                if active["exit_time"] <= trade["entry_time"]:
                    daily_bp += (active["margin_used"] + active["pnl"])
                    running_equity += active["pnl"]
                    all_trades.append(active["record"])
                    active_day_positions.remove(active)

            risk_amt = running_equity * (risk_pct / 100)
            one_r = abs(trade["entry_price"] - trade["sl"])
            desired_shares = int(risk_amt / one_r) if one_r > 0 else 1

            max_affordable = int((daily_bp * MIS_LEVERAGE) / trade["entry_price"]) if trade["entry_price"] > 0 else 0
            actual_shares = min(desired_shares, max_affordable)

            if actual_shares > 0:
                trade_value = actual_shares * trade["entry_price"]
                margin_used = trade_value / MIS_LEVERAGE
                daily_bp -= margin_used

                raw_pnl = (trade["exit_price"] - trade["entry_price"]) * actual_shares
                turnover = (trade["entry_price"] + trade["exit_price"]) * actual_shares
                fees_and_taxes = turnover * 0.0005
                pnl = raw_pnl - fees_and_taxes

                record = {
                    "symbol":      trade["symbol"],
                    "strategy":    "VWAP_RUNNER",
                    "entry_date":  f"{trade['date']} {trade['entry_time'][:5]}",
                    "exit_date":   f"{trade['date']} {trade['exit_time'][:5]}",
                    "entry":       round(trade["entry_price"], 2),
                    "exit":        round(trade["exit_price"], 2),
                    "qty":         actual_shares,
                    "pnl":         round(pnl, 2),
                    "pnl_pct":     round((pnl / (trade["entry_price"] * actual_shares)) * 100, 2) if trade["entry_price"] > 0 else 0,
                    "exit_reason": trade["reason"]
                }

                active_day_positions.append({
                    "exit_time":   trade["exit_time"],
                    "margin_used": margin_used,
                    "pnl":         pnl,
                    "record":      record,
                })

        for active in active_day_positions:
            running_equity += active["pnl"]
            all_trades.append(active["record"])

    return all_trades


def _compute_stats(trades: list[dict], initial_capital: float) -> dict:
    """Compute aggregated backtest statistics."""
    if not trades:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate": 0, "avg_gain_pct": 0, "avg_loss_pct": 0,
            "profit_factor": 0, "max_drawdown": 0,
            "final_capital": initial_capital, "total_return_pct": 0,
        }

    winners = [t for t in trades if t["pnl"] > 0]
    losers  = [t for t in trades if t["pnl"] <= 0]

    gross_profit = sum(t["pnl"] for t in winners)
    gross_loss   = abs(sum(t["pnl"] for t in losers))
    net_pnl      = sum(t["pnl"] for t in trades)
    final_cap    = initial_capital + net_pnl

    win_rate    = len(winners) / len(trades) * 100
    avg_gain    = (gross_profit / len(winners)) if winners else 0
    avg_loss    = (gross_loss   / len(losers))  if losers  else 0
    pf          = (gross_profit / gross_loss) if gross_loss > 0 else float("inf")

    # Equity curve & drawdown
    curve  = [initial_capital]
    equity = initial_capital
    peak   = initial_capital
    max_dd = 0
    for t in trades:
        equity += t["pnl"]
        curve.append(round(equity, 2))
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100
        if dd > max_dd:
            max_dd = dd

    return {
        "total_trades":    len(trades),
        "winning_trades":  len(winners),
        "losing_trades":   len(losers),
        "win_rate":        round(win_rate, 1),
        "avg_gain_pct":    round(avg_gain / initial_capital * 100, 2),
        "avg_loss_pct":    round(avg_loss  / initial_capital * 100, 2),
        "profit_factor":   round(pf, 2),
        "max_drawdown":    round(max_dd, 2),
        "final_capital":   round(final_cap, 2),
        "total_return_pct": round(net_pnl / initial_capital * 100, 2),
    }


def run_backtest(
    db: Session,
    user: User,
    client: GrowwClient,
    request: BacktestRequest,
    progress_callback: Optional[Callable] = None,
) -> BacktestResult:
    """
    Run full backtest and save results to DB.
    Returns a BacktestResult ORM object.
    """
    symbols = request.symbols or STOCK_UNIVERSE
    capital = request.capital
    all_trades = []

    logger.info(f"Backtest starting: {request.strategy} {request.start_date}→{request.end_date} cap={capital} (User {user.username})")

    # Strategy Selector Routing
    if request.strategy in ["HARMAN1_PULLBACK", "SWING"]:
        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
        lookback_start = (start_dt - timedelta(days=200)).strftime("%Y-%m-%d")

        market_data = {}
        for idx, symbol in enumerate(symbols, 1):
            if progress_callback:
                progress_callback(idx, len(symbols), symbol)
            try:
                raw = client.get_historical_data(symbol, lookback_start, request.end_date)
                if not raw or len(raw) < 50:
                    continue
                df = pd.DataFrame(raw)
                df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
                df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
                df["high"]   = pd.to_numeric(df["high"],   errors="coerce")
                df["low"]    = pd.to_numeric(df["low"],    errors="coerce")
                df["open"]   = pd.to_numeric(df["open"],   errors="coerce")
                df           = df.dropna(subset=["close"])
                df           = _build_indicators(df)
                
                df["date_idx"] = pd.to_datetime(df["date"]).dt.date
                df.set_index("date_idx", inplace=True)
                market_data[symbol] = df
            except Exception as e:
                logger.warning(f"Backtest data fetch error for {symbol}: {e}")

        all_trades = _simulate_swing_trades(
            market_data,
            start_dt.date(),
            datetime.strptime(request.end_date, "%Y-%m-%d").date(),
            capital,
            user.risk_pct
        )

    elif request.strategy in ["VWAP_RUNNER", "INTRADAY"]:
        market_data = {}
        for idx, symbol in enumerate(symbols, 1):
            if progress_callback:
                progress_callback(idx, len(symbols), symbol)
            try:
                # Intraday 5m data
                raw = client.get_historical_intraday_data(symbol, request.start_date, request.end_date)
                if not raw or len(raw) < 5:
                    continue
                df = pd.DataFrame(raw)
                df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
                df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
                df["high"]   = pd.to_numeric(df["high"],   errors="coerce")
                df["low"]    = pd.to_numeric(df["low"],    errors="coerce")
                df["open"]   = pd.to_numeric(df["open"],   errors="coerce")
                df           = df.dropna(subset=["close"])
                market_data[symbol] = df
            except Exception as e:
                logger.warning(f"Backtest 5m data fetch error for {symbol}: {e}")

        all_trades = _simulate_intraday_trades(
            market_data,
            capital,
            user.risk_pct
        )

    else:
        # Default VCP walk-forward simulation (Symbol by Symbol)
        for idx, symbol in enumerate(symbols, 1):
            if progress_callback:
                progress_callback(idx, len(symbols), symbol)
            time.sleep(0.1)

            try:
                raw = client.get_historical_data(symbol, request.start_date, request.end_date)
                if not raw or len(raw) < 80:
                    continue

                df = pd.DataFrame(raw)
                df["close"]  = pd.to_numeric(df["close"],  errors="coerce")
                df["volume"] = pd.to_numeric(df.get("volume", 0), errors="coerce").fillna(0)
                df["high"]   = pd.to_numeric(df["high"],   errors="coerce")
                df["low"]    = pd.to_numeric(df["low"],    errors="coerce")
                df           = df.dropna(subset=["close"])
                df           = _build_indicators(df)

                trades = _simulate_vcp_trades(
                    df, symbol, capital,
                    user.risk_pct, user.max_sl_pct
                )
                all_trades.extend(trades)

            except Exception as e:
                logger.warning(f"Backtest VCP error for {symbol}: {e}")

    stats = _compute_stats(all_trades, capital)

    # Build equity curve with dates
    equity_curve = []
    running = capital
    equity_curve.append({"date": request.start_date, "equity": capital})
    for t in sorted(all_trades, key=lambda x: x.get("exit_date", "")):
        running += t["pnl"]
        equity_curve.append({"date": t["exit_date"], "equity": round(running, 2)})

    result = BacktestResult(
        user_id         = user.id,
        strategy        = request.strategy,
        start_date      = request.start_date,
        end_date        = request.end_date,
        initial_capital = capital,
        final_capital   = stats["final_capital"],
        max_drawdown    = stats["max_drawdown"],
        total_trades    = stats["total_trades"],
        winning_trades  = stats["winning_trades"],
        losing_trades   = stats["losing_trades"],
        win_rate        = stats["win_rate"],
        avg_gain_pct    = stats["avg_gain_pct"],
        avg_loss_pct    = stats["avg_loss_pct"],
        profit_factor   = stats["profit_factor"],
        total_return_pct = stats["total_return_pct"],
        trade_log       = all_trades,
        equity_curve    = equity_curve,
    )
    db.add(result)
    db.commit()
    db.refresh(result)
    logger.info(f"Backtest complete (User {user.username}): {result}")
    return result
