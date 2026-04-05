"""
forward_test.py
---------------
Server-side persistence for the forward test.
All data is saved in data/forward_test.json.
This survives browser refreshes, closing the tab, and restarting the bot.
"""

import json
import os
import logging
from datetime import datetime
from typing import List, Dict

from config import FORWARD_TEST_DB, TRADING_CAPITAL

logger = logging.getLogger(__name__)


def _load() -> dict:
    """Load the full forward test database from disk."""
    if not os.path.exists(FORWARD_TEST_DB):
        return {"trades": [], "started": None, "capital": TRADING_CAPITAL}
    try:
        with open(FORWARD_TEST_DB, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"trades": [], "started": None, "capital": TRADING_CAPITAL}


def _save(db: dict):
    """Save the forward test database to disk."""
    os.makedirs("data", exist_ok=True)
    with open(FORWARD_TEST_DB, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, default=str)


def get_all() -> dict:
    """Return the full forward test database."""
    return _load()


def add_trade(signal: dict) -> dict:
    """
    Add a new signal to the forward test.
    Returns the created trade record, or raises ValueError if duplicate.
    """
    db = _load()
    trade_id = f"{signal['symbol']}_{signal.get('scan_date', datetime.now().strftime('%Y-%m-%d'))}"

    if any(t["id"] == trade_id for t in db["trades"]):
        raise ValueError(f"{signal['symbol']} is already in your forward test for this date.")

    one_r = signal["entry_price"] - signal["stop_loss"]

    trade = {
        "id":           trade_id,
        "symbol":       signal["symbol"],
        "strategy":     signal.get("strategy", "VCP"),
        "scan_date":    signal.get("scan_date", datetime.now().strftime("%Y-%m-%d")),
        "entry_price":  signal["entry_price"],
        "stop_loss":    signal["stop_loss"],
        "sl_pct":       signal["sl_pct"],
        "shares":       signal.get("shares", 0),
        "invested":     signal.get("invested", 0),
        "risk_amount":  signal.get("risk_amount", 0),
        "one_r":        round(one_r, 2),
        "targets": {
            "breakeven": round(signal["entry_price"] + 2 * one_r, 2),
            "three_r":   round(signal["entry_price"] + 3 * one_r, 2),
            "four_r":    round(signal["entry_price"] + 4 * one_r, 2),
            "six_r":     round(signal["entry_price"] + 6 * one_r, 2),
            "ten_r":     round(signal["entry_price"] + 10 * one_r, 2),
        },
        "quality_score": signal.get("quality_score", 0),
        "pullback_pct":  signal.get("pullback_pct", 0),
        "vol_ratio":     signal.get("vol_ratio", 1.0),
        "notes":         signal.get("notes", ""),
        "status":        "WATCHING",   # WATCHING → ACTIVE → CLOSED
        "entry_date":    None,
        "exit_date":     None,
        "exit_price":    None,
        "exit_reason":   None,
        "realized_pnl":  0,
        "pnl_pct":       0,
        "added_at":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    if db["started"] is None:
        db["started"] = datetime.now().strftime("%Y-%m-%d")

    db["trades"].append(trade)
    _save(db)
    return trade


def mark_entered(trade_id: str, actual_entry_price: float = None) -> dict:
    """Mark a WATCHING trade as ACTIVE (entry triggered)."""
    db = _load()
    for t in db["trades"]:
        if t["id"] == trade_id:
            if t["status"] != "WATCHING":
                raise ValueError("Trade is not in WATCHING status")
            t["status"]     = "ACTIVE"
            t["entry_date"] = datetime.now().strftime("%Y-%m-%d")
            if actual_entry_price:
                t["entry_price"] = actual_entry_price
            _save(db)
            return t
    raise ValueError(f"Trade {trade_id} not found")


def close_trade(trade_id: str, exit_price: float, exit_reason: str) -> dict:
    """Close an ACTIVE or WATCHING trade with an exit price."""
    db = _load()
    for t in db["trades"]:
        if t["id"] == trade_id:
            if t["status"] == "CLOSED":
                raise ValueError("Trade is already closed")
            pnl_per_share = exit_price - t["entry_price"]
            shares        = t.get("shares", 0)
            pnl_rs        = round(pnl_per_share * shares, 2)
            pnl_pct       = round(pnl_per_share / t["entry_price"] * 100, 2) if t["entry_price"] else 0

            t["status"]       = "CLOSED"
            t["exit_date"]    = datetime.now().strftime("%Y-%m-%d")
            t["exit_price"]   = exit_price
            t["exit_reason"]  = exit_reason
            t["realized_pnl"] = pnl_rs
            t["pnl_pct"]      = pnl_pct
            _save(db)
            return t
    raise ValueError(f"Trade {trade_id} not found")


def delete_trade(trade_id: str) -> bool:
    """Remove a trade from the forward test (e.g. signal never triggered)."""
    db = _load()
    before = len(db["trades"])
    db["trades"] = [t for t in db["trades"] if t["id"] != trade_id]
    if len(db["trades"]) < before:
        _save(db)
        return True
    return False


def get_summary() -> dict:
    """Compute summary statistics for the forward test."""
    db    = _load()
    trades = db["trades"]
    closed = [t for t in trades if t["status"] == "CLOSED"]
    active = [t for t in trades if t["status"] == "ACTIVE"]
    watching = [t for t in trades if t["status"] == "WATCHING"]
    wins   = [t for t in closed if t["realized_pnl"] > 0]
    losses = [t for t in closed if t["realized_pnl"] <= 0]

    cap    = db.get("capital", TRADING_CAPITAL)
    total_pnl = sum(t["realized_pnl"] for t in closed)

    # Equity curve for the forward test
    eq = cap
    equity_curve = [{"date": db.get("started") or datetime.now().strftime("%Y-%m-%d"), "equity": eq}]
    for t in sorted(closed, key=lambda x: x.get("exit_date") or ""):
        eq += t["realized_pnl"]
        equity_curve.append({"date": t["exit_date"], "equity": round(eq, 2)})

    return {
        "started":         db.get("started"),
        "capital":         cap,
        "total_trades":    len(trades),
        "watching":        len(watching),
        "active":          len(active),
        "closed":          len(closed),
        "wins":            len(wins),
        "losses":          len(losses),
        "win_rate":        round(len(wins) / len(closed) * 100, 1) if closed else 0,
        "total_pnl":       round(total_pnl, 2),
        "total_return_pct": round(total_pnl / cap * 100, 2) if cap else 0,
        "avg_win_pct":     round(sum(t["pnl_pct"] for t in wins) / len(wins), 2) if wins else 0,
        "avg_loss_pct":    round(sum(t["pnl_pct"] for t in losses) / len(losses), 2) if losses else 0,
        "profit_factor":   round(
            sum(t["realized_pnl"] for t in wins) / abs(sum(t["realized_pnl"] for t in losses)), 2
        ) if losses and sum(t["realized_pnl"] for t in losses) != 0 else 999,
        "final_equity":    round(cap + total_pnl, 2),
        "equity_curve":    equity_curve,
        "trades":          trades,
    }