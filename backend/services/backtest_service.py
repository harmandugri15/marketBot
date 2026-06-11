"""
services/backtest_service.py
-----------------------------
Backtesting engine for VCP and intraday strategies.
Ported from the original backtester.py, restructured for DB persistence
and proper separation of data fetching vs simulation logic.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Callable, Optional

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from config import get_settings, STOCK_UNIVERSE
from core.indicators import detect_vcp, add_emas
from core.groww_client import GrowwClient
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
    df["rsi"] = 100 - (100 / (1 + (gain / loss)))
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
                    "exit_reason": "TARGET_HIT",
                    "entry_date":  str(entry_date),
                    "exit_date":   str(df.index[i]),
                })
                in_trade = False

    return trades


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

    logger.info(f"Backtest starting: {request.strategy} {request.start_date}→{request.end_date} cap={capital}")

    for idx, symbol in enumerate(symbols, 1):
        if progress_callback:
            progress_callback(idx, len(symbols), symbol)
        time.sleep(0.3)

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
                settings.risk_pct, settings.max_sl_pct
            )
            all_trades.extend(trades)

        except Exception as e:
            logger.warning(f"Backtest error for {symbol}: {e}")

    stats = _compute_stats(all_trades, capital)

    # Build equity curve with dates
    equity_curve = []
    running = capital
    equity_curve.append({"date": request.start_date, "equity": capital})
    for t in sorted(all_trades, key=lambda x: x.get("exit_date", "")):
        running += t["pnl"]
        equity_curve.append({"date": t["exit_date"], "equity": round(running, 2)})

    result = BacktestResult(
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
    logger.info(f"Backtest complete: {result}")
    return result
