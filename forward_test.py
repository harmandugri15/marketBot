import json
import os
from datetime import datetime
from config import FORWARD_TEST_DB, get_settings

def _load():
    if not os.path.exists(FORWARD_TEST_DB): return {"trades": [], "started": None}
    with open(FORWARD_TEST_DB, "r", encoding="utf-8") as f: return json.load(f)

def _save(db):
    with open(FORWARD_TEST_DB, "w", encoding="utf-8") as f: json.dump(db, f, indent=2)

def add_trade(signal):
    db = _load()
    trade_id = f"{signal['symbol']}_{datetime.now().strftime('%Y%m%d')}"
    if any(t["id"] == trade_id for t in db["trades"]): raise ValueError("Trade exists")
    
    trade = {
        "id": trade_id, "symbol": signal["symbol"], "strategy": signal["strategy"],
        "entry_price": signal["entry_price"], "stop_loss": signal["stop_loss"],
        "sl_pct": signal["sl_pct"], "shares": signal["shares"], "status": "WATCHING",
        "entry_date": None, "exit_date": None, "realized_pnl": 0, "pnl_pct": 0, "notes": signal.get("notes", "")
    }
    if not db["started"]: db["started"] = datetime.now().strftime("%Y-%m-%d")
    db["trades"].append(trade)
    _save(db)
    return trade

def mark_entered(trade_id, price=None):
    db = _load()
    for t in db["trades"]:
        if t["id"] == trade_id:
            t["status"], t["entry_date"] = "ACTIVE", datetime.now().strftime("%Y-%m-%d")
            if price: t["entry_price"] = price
            _save(db); return t
    raise ValueError("Not found")

def close_trade(trade_id, exit_px, reason):
    db = _load()
    for t in db["trades"]:
        if t["id"] == trade_id:
            t["status"], t["exit_date"], t["exit_price"], t["exit_reason"] = "CLOSED", datetime.now().strftime("%Y-%m-%d"), exit_px, reason
            t["realized_pnl"] = round((exit_px - t["entry_price"]) * t["shares"], 2)
            t["pnl_pct"] = round((exit_px - t["entry_price"]) / t["entry_price"] * 100, 2)
            _save(db); return t

def delete_trade(trade_id):
    db = _load()
    db["trades"] = [t for t in db["trades"] if t["id"] != trade_id]
    _save(db); return True

def get_summary():
    db = _load(); settings = get_settings(); cap = settings['capital']
    closed = [t for t in db["trades"] if t["status"] == "CLOSED"]
    pnl = sum(t["realized_pnl"] for t in closed)
    wins = [t for t in closed if t["realized_pnl"] > 0]
    
    eq = cap; curve = [{"date": db["started"] or "Today", "equity": cap}]
    for t in sorted(closed, key=lambda x: x["exit_date"]):
        eq += t["realized_pnl"]
        curve.append({"date": t["exit_date"], "equity": round(eq, 2)})

    return {
        "capital": cap, "total_pnl": round(pnl, 2), "win_rate": round(len(wins)/len(closed)*100, 1) if closed else 0,
        "active": len([t for t in db["trades"] if t["status"] == "ACTIVE"]),
        "watching": len([t for t in db["trades"] if t["status"] == "WATCHING"]),
        "closed": len(closed), "equity_curve": curve, "trades": db["trades"]
    }