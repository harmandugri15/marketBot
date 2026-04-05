"""
backtester.py
-------------
Bar-by-bar simulation of DEP and VT strategies.
No look-ahead bias: each day only sees data up to that point.
"""

import logging
import json
import os
import time
from datetime import datetime, timedelta
from typing import List

import pandas as pd

from config import (
    STOCK_UNIVERSE, TRADING_CAPITAL, RISK_PER_TRADE_PCT,
    BACKTEST_START_DATE, BACKTEST_END_DATE, BACKTEST_DB,
    CIRCUIT_BREAKER_PCT
)

logger = logging.getLogger(__name__)


class BacktestTrade:
    def __init__(self, symbol, entry_date, entry_price, stop_loss, shares, one_r, strategy):
        self.symbol       = symbol
        self.entry_date   = entry_date
        self.entry_price  = entry_price
        self.stop_loss    = stop_loss
        self.shares       = shares
        self.one_r        = one_r
        self.strategy     = strategy
        self.target_3r    = entry_price + 3 * one_r
        self.target_4r    = entry_price + 4 * one_r

        half = max(1, shares // 2)
        self.tranche1     = half
        self.tranche2     = shares - half
        self.remaining    = shares

        self.partial_done = False
        self.exit_date    = None
        self.exit_price   = None
        self.exit_reason  = None
        self.pnl          = 0.0
        self.pnl_pct      = 0.0
        self.is_closed    = False

    def to_dict(self):
        return {
            "symbol":      self.symbol,
            "strategy":    self.strategy,
            "entry_date":  str(self.entry_date)[:10],
            "entry_price": round(self.entry_price, 2),
            "stop_loss":   round(self.stop_loss, 2),
            "exit_date":   str(self.exit_date)[:10] if self.exit_date else None,
            "exit_price":  round(self.exit_price, 2) if self.exit_price else None,
            "shares":      self.shares,
            "pnl":         round(self.pnl, 2),
            "pnl_pct":     round(self.pnl_pct, 2),
            "exit_reason": self.exit_reason,
            "one_r":       round(self.one_r, 2),
            "is_win":      self.pnl > 0,
        }


def _simulate_stock(symbol: str, df: pd.DataFrame, capital: float, strategy: str) -> List[dict]:
    """Run the bar-by-bar simulation for one stock. Returns list of completed trade dicts."""
    trades = []
    active: BacktestTrade = None
    pending = None
    last_expansion_i = -999

    if len(df) < 100:
        return trades

    # Indicators
    df = df.copy()
    df["ema10"]     = df["close"].ewm(span=10, adjust=False).mean()
    df["ema20"]     = df["close"].ewm(span=20, adjust=False).mean()
    df["vol_sma50"] = df["volume"].rolling(50).mean()
    df["daily_ret"] = df["close"].pct_change() * 100
    exp12           = df["close"].ewm(span=12, adjust=False).mean()
    exp26           = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"]      = exp12 - exp26
    df["macd_sig"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["pivot"]     = (df["high"].shift(1) + df["low"].shift(1) + df["close"].shift(1)) / 3

    for i in range(100, len(df)):
        today = df.iloc[i]
        yest  = df.iloc[i - 1]

        # ── 1. MANAGE OPEN TRADE ──────────────────────────────────────────────
        if active and not active.is_closed:
            lo    = today["low"]
            hi    = today["high"]
            cl    = today["close"]
            op    = today["open"]
            ema20 = today["ema20"]

            # Stop loss — use open if gapped below SL
            if lo <= active.stop_loss:
                exit_px = min(op, active.stop_loss)
                active.pnl      += (exit_px - active.entry_price) * active.remaining
                active.exit_price = exit_px
                active.exit_date  = today.name
                active.exit_reason = "Break Even" if active.partial_done else "Stop Loss Hit"
                active.pnl_pct    = active.pnl / (active.entry_price * active.shares) * 100
                active.is_closed  = True
                trades.append(active.to_dict())
                active = None
                continue

            # Partial exit at 3R (sell half)
            if not active.partial_done and hi >= active.target_3r:
                active.pnl          += (active.target_3r - active.entry_price) * active.tranche1
                active.remaining    -= active.tranche1
                active.partial_done  = True
                active.stop_loss     = active.entry_price  # move to breakeven

            # Trail remaining on 20 EMA
            if active.partial_done and cl < ema20:
                active.pnl      += (cl - active.entry_price) * active.remaining
                active.remaining = 0
                active.exit_price = cl
                active.exit_date  = today.name
                active.exit_reason = "20 EMA Trail"
                active.pnl_pct    = active.pnl / (active.entry_price * active.shares) * 100
                active.is_closed  = True
                trades.append(active.to_dict())
                active = None
            continue

        # ── 2. FILL PENDING ENTRY ─────────────────────────────────────────────
        if pending:
            if today["open"] > pending["trigger"] * 1.05:
                pending = None  # gapped up too far — skip
            elif today["high"] >= pending["trigger"]:
                fill    = max(today["open"], pending["trigger"])
                one_r   = fill - pending["sl"]
                if one_r > 0:
                    risk_amt = capital * (RISK_PER_TRADE_PCT / 100)
                    shares   = int(risk_amt / one_r)
                    if shares * fill > capital:
                        shares = int(capital / fill)
                    if shares > 0:
                        active = BacktestTrade(
                            symbol      = symbol,
                            entry_date  = today.name,
                            entry_price = fill,
                            stop_loss   = pending["sl"],
                            shares      = shares,
                            one_r       = one_r,
                            strategy    = strategy
                        )
            pending = None

        # ── 3. LOOK FOR NEW SETUP ─────────────────────────────────────────────
        if strategy == "DEP":
            # Expansion day detection
            vol_avg = today.get("vol_sma50", 0)
            if (vol_avg > 0
                    and today["daily_ret"] >= 4.0
                    and today["volume"] >= 2.0 * vol_avg):
                prior_close = df.iloc[max(0, i - 20)]["close"]
                run_up = (today["close"] - prior_close) / prior_close * 100
                if run_up < 40:
                    last_expansion_i = i
                    continue

            days_since = i - last_expansion_i
            if 1 <= days_since <= 15:
                vol_avg = today.get("vol_sma50", 0)
                if vol_avg > 0 and today["volume"] <= vol_avg * 1.5:
                    rng_pct = (today["high"] - today["low"]) / today["low"] * 100
                    ema10   = today.get("ema10", 0)
                    if rng_pct <= 5.0 and ema10 > 0:
                        dist = abs(today["low"] - ema10) / ema10 * 100
                        if dist <= 3.5:
                            trig   = round(today["high"] + 0.05, 2)
                            sl     = round(today["low"]  - 0.05, 2)
                            sl_pct = (trig - sl) / trig * 100
                            if 0.5 <= sl_pct <= 6.0:
                                pending = {"trigger": trig, "sl": sl}

        elif strategy == "VT":
            ema20 = today.get("ema20", 0)
            pivot = today.get("pivot", 0)
            if ema20 <= 0 or pivot <= 0:
                continue
            if abs(today["open"] - today["high"]) < 0.01:
                continue
            if today["close"] < ema20 or today["close"] < pivot:
                continue
            y_ema20 = yest.get("ema20", 0)
            crossed = y_ema20 > 0 and yest["close"] < y_ema20 and today["close"] > ema20
            bounced = today["low"] <= ema20 * 1.005 and today["close"] > ema20
            if not (crossed or bounced):
                continue
            if today.get("macd_hist", 0) <= yest.get("macd_hist", 0):
                continue

            trig   = round(today["high"] + 0.05, 2)
            sl     = round(today["low"]  - 0.05, 2)
            sl_pct = (trig - sl) / trig * 100
            if 0.5 <= sl_pct <= 7.0:
                pending = {"trigger": trig, "sl": sl}

    # Force-close at end of period
    if active and not active.is_closed:
        last = df.iloc[-1]
        pnl  = (last["close"] - active.entry_price) * active.remaining + active.pnl
        active.pnl        = pnl
        active.exit_price = last["close"]
        active.exit_date  = last.name
        active.exit_reason = "Backtest End"
        active.pnl_pct    = active.pnl / (active.entry_price * active.shares) * 100
        active.is_closed  = True
        trades.append(active.to_dict())

    return trades


def compute_metrics(trades: List[dict], capital: float) -> dict:
    if not trades:
        return {
            "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
            "win_rate": 0, "total_pnl": 0, "total_return_pct": 0,
            "avg_win_pct": 0, "avg_loss_pct": 0, "profit_factor": 0,
            "max_drawdown_pct": 0, "best_trade_pct": 0, "worst_trade_pct": 0,
            "avg_holding_days": 0, "final_equity": capital
        }

    wins   = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    total_pnl   = sum(t["pnl"] for t in trades)
    total_win   = sum(t["pnl"] for t in wins)
    total_loss  = abs(sum(t["pnl"] for t in losses))
    pf          = round(total_win / total_loss, 2) if total_loss > 0 else 999

    # Drawdown
    eq = capital; peak = eq; max_dd = 0
    for t in trades:
        eq += t["pnl"]
        peak = max(peak, eq)
        dd   = (peak - eq) / peak * 100
        max_dd = max(max_dd, dd)

    # Holding days
    hdays = []
    for t in trades:
        try:
            d1 = datetime.strptime(t["entry_date"], "%Y-%m-%d")
            d2 = datetime.strptime(t["exit_date"],  "%Y-%m-%d")
            hdays.append((d2 - d1).days)
        except Exception:
            pass

    return {
        "total_trades":    len(trades),
        "winning_trades":  len(wins),
        "losing_trades":   len(losses),
        "win_rate":        round(len(wins) / len(trades) * 100, 1),
        "total_pnl":       round(total_pnl, 2),
        "total_return_pct": round(total_pnl / capital * 100, 2),
        "avg_win_pct":     round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss_pct":    round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0,
        "profit_factor":   pf,
        "max_drawdown_pct": round(max_dd, 2),
        "best_trade_pct":  round(max(t["pnl_pct"] for t in trades), 2),
        "worst_trade_pct": round(min(t["pnl_pct"] for t in trades), 2),
        "avg_holding_days": round(sum(hdays) / len(hdays)) if hdays else 0,
        "final_equity":    round(capital + total_pnl, 2),
    }


def run_backtest(api, start_date=None, end_date=None, capital=None,
                 symbols=None, progress_callback=None, strategy="DEP"):
    start_date = start_date or BACKTEST_START_DATE
    end_date   = end_date   or BACKTEST_END_DATE
    capital    = capital    or TRADING_CAPITAL
    symbols    = symbols    or STOCK_UNIVERSE

    failure_threshold = capital * (CIRCUIT_BREAKER_PCT / 100)
    all_trades = []
    running_equity = capital
    total = len(symbols)

    for idx, symbol in enumerate(symbols, 1):
        if progress_callback:
            progress_callback(idx, total, symbol)

        # Circuit breaker
        if running_equity < failure_threshold:
            logger.error("CIRCUIT BREAKER: account lost 50%+. Stopping backtest.")
            break

        try:
            warm_start = (datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=200)).strftime("%Y-%m-%d")
            raw = api.get_historical_data(symbol, from_date=warm_start, to_date=end_date)
            if not raw:
                continue

            df = pd.DataFrame(raw)
            df.columns = [c.lower().strip() for c in df.columns]
            rename = {"timestamp": "date", "datetime": "date", "o": "open",
                      "h": "high", "l": "low", "c": "close", "v": "volume"}
            df.rename(columns=rename, inplace=True)
            if not all(c in df.columns for c in ["date", "close", "volume"]):
                continue
            df["date"] = pd.to_datetime(df["date"])
            df.sort_values("date", inplace=True)
            df.set_index("date", inplace=True)
            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
            df.dropna(subset=["close", "volume"], inplace=True)

            if len(df) < 110:
                continue

            sym_trades = _simulate_stock(symbol, df, capital, strategy)
            # Only count trades that started inside the backtest window
            sym_trades = [t for t in sym_trades
                          if t["entry_date"] and t["entry_date"] >= start_date]
            all_trades.extend(sym_trades)

            for t in sym_trades:
                running_equity += t["pnl"]

        except Exception as e:
            logger.error(f"Backtest error {symbol}: {e}")

        time.sleep(0.1)

    all_trades.sort(key=lambda t: t["entry_date"])

    # Build equity curve (one point per trade exit)
    eq = capital
    equity_curve = [{"date": start_date, "equity": round(eq, 2)}]
    for t in all_trades:
        eq += t["pnl"]
        if t["exit_date"]:
            equity_curve.append({"date": t["exit_date"], "equity": round(eq, 2)})

    metrics = compute_metrics(all_trades, capital)

    results = {
        "start_date":       start_date,
        "end_date":         end_date,
        "starting_capital": capital,
        "strategy_run":     strategy,
        "metrics":          metrics,
        "trades":           all_trades,
        "equity_curve":     equity_curve,
        "run_timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    os.makedirs("data", exist_ok=True)
    with open(BACKTEST_DB, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(
        f"Backtest done: {metrics['total_trades']} trades | "
        f"WR {metrics['win_rate']}% | PF {metrics['profit_factor']} | "
        f"Return {metrics['total_return_pct']}%"
    )
    return results


def load_backtest_results() -> dict:
    if not os.path.exists(BACKTEST_DB):
        return {}
    try:
        with open(BACKTEST_DB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}