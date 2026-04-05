"""
trade_manager.py — Manages paper and live trades.
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict

from config import PAPER_TRADING, TRADING_CAPITAL, TRADES_DB

logger = logging.getLogger(__name__)


def load_trades() -> List[Dict]:
    if not os.path.exists(TRADES_DB):
        return []
    try:
        with open(TRADES_DB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_trades(trades: List[Dict]):
    os.makedirs("data", exist_ok=True)
    with open(TRADES_DB, "w", encoding="utf-8") as f:
        json.dump(trades, f, indent=2, default=str)


def get_active_trades() -> List[Dict]:
    return [t for t in load_trades() if t.get("status") in ("ACTIVE", "PARTIAL")]


def get_all_trades() -> List[Dict]:
    return load_trades()


def open_trade(api, signal: dict) -> dict:
    """
    Open a new paper or live trade from a scanner signal.
    Handles both old-style (no targets key) and new-style signals safely.
    """
    entry = signal["entry_price"]
    sl    = signal["stop_loss"]
    one_r = entry - sl

    # Build targets if not present (backwards compat)
    targets = signal.get("targets") or {
        "one_r":            round(one_r, 2),
        "breakeven_trigger": round(entry + 2 * one_r, 2),
        "partial_exit_1":   round(entry + 4 * one_r, 2),
        "two_r_price":      round(entry + 2 * one_r, 2),
        "four_r_price":     round(entry + 4 * one_r, 2),
        "six_r_price":      round(entry + 6 * one_r, 2),
        "ten_r_price":      round(entry + 10 * one_r, 2),
    }

    shares = signal.get("shares", 0)
    trade = {
        "id":          f"{signal['symbol']}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "symbol":      signal["symbol"],
        "strategy":    signal.get("strategy", "VCP"),
        "entry_date":  datetime.now().strftime("%Y-%m-%d"),
        "entry_time":  datetime.now().strftime("%H:%M:%S"),
        "entry_price": entry,
        "stop_loss":   sl,
        "sl_pct":      signal.get("sl_pct", round((entry - sl) / entry * 100, 2)),
        "shares":      shares,
        "invested":    signal.get("invested", round(shares * entry, 2)),
        "risk_amount": signal.get("risk_amount", round(TRADING_CAPITAL * 0.02, 2)),
        "targets":     targets,
        "one_r":       targets["one_r"],
        "tranche1_shares":  max(1, shares // 3),
        "tranche2_shares":  max(1, shares // 3),
        "tranche3_shares":  shares - 2 * max(1, shares // 3),
        "remaining_shares": shares,
        "breakeven_moved":  False,
        "tranche1_exited":  False,
        "tranche2_exited":  False,
        "exit_date":   None,
        "exit_price":  None,
        "exit_reason": None,
        "realized_pnl": 0,
        "pnl_pct":     0,
        "buy_order_id": None,
        "sell_order_ids": [],
        "status":      "ACTIVE",
        "paper_trade": PAPER_TRADING,
        "notes":       []
    }

    if PAPER_TRADING:
        logger.info(f"[PAPER] BUY {shares} x {signal['symbol']} @ Rs{entry}")
        trade["notes"].append(f"Paper buy at Rs{entry}")
    else:
        try:
            order = api.place_order(
                symbol="NSE", exchange="NSE",
                transaction_type="BUY", quantity=shares,
                order_type="LIMIT", price=entry, product="CNC"
            )
            trade["buy_order_id"] = order.get("order_id")
            trade["notes"].append(f"Live buy order {order.get('order_id')}")
        except Exception as e:
            logger.error(f"Buy order failed for {signal['symbol']}: {e}")
            trade["status"] = "ERROR"
            trade["notes"].append(f"Buy failed: {e}")

    trades = load_trades()
    trades.append(trade)
    save_trades(trades)
    return trade


def get_portfolio_summary() -> dict:
    trades  = load_trades()
    active  = [t for t in trades if t["status"] in ("ACTIVE", "PARTIAL")]
    closed  = [t for t in trades if t["status"] == "CLOSED"]
    wins    = [t for t in closed if t.get("realized_pnl", 0) > 0]
    losses  = [t for t in closed if t.get("realized_pnl", 0) <= 0]
    pnl     = sum(t.get("realized_pnl", 0) for t in closed)

    return {
        "active_trades":  len(active),
        "closed_trades":  len(closed),
        "total_trades":   len(trades),
        "realized_pnl":   round(pnl, 2),
        "win_rate":       round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "wins":           len(wins),
        "losses":         len(losses),
        "active_list":    active,
        "recent_closed":  sorted(closed, key=lambda t: t.get("exit_date", ""), reverse=True)[:10],
    }