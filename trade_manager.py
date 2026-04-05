import os
import json
import logging
from datetime import datetime
from config import TRADES_DB, get_settings

logger = logging.getLogger(__name__)

def load_trades():
    if not os.path.exists(TRADES_DB): return []
    with open(TRADES_DB, "r") as f: return json.load(f)

def save_trades(trades):
    with open(TRADES_DB, "w") as f: json.dump(trades, f, indent=2)

def open_trade(api, signal):
    settings = get_settings()
    entry, sl = signal["entry_price"], signal["stop_loss"]
    
    # Dynamic Position Sizing
    risk_amt = settings['capital'] * (settings['risk_pct'] / 100)
    shares = int(risk_amt / (entry - sl)) if (entry - sl) > 0 else 0
    
    # Student Override: If math says 0 shares, buy 1 if affordable
    if shares == 0 and entry <= settings['capital']: shares = 1
    
    if shares == 0: raise ValueError("Insufficient capital for 1 share")

    trade = {
        "id": f"{signal['symbol']}_{datetime.now().strftime('%H%M%S')}",
        "symbol": signal["symbol"], "strategy": signal["strategy"],
        "entry_price": entry, "stop_loss": sl, "shares": shares,
        "status": "ACTIVE", "paper_mode": settings.get("paper_trading", True)
    }

    if not trade["paper_mode"]:
        try:
            api.place_order(symbol=signal["symbol"], quantity=shares, price=entry, transaction_type="BUY")
            logger.info(f"LIVE ORDER: Bought {shares} {signal['symbol']}")
        except Exception as e:
            logger.error(f"Live order failed: {e}")
            trade["status"] = "ERROR"

    all_t = load_trades()
    all_t.append(trade)
    save_trades(all_t)
    return trade

def get_portfolio_summary():
    trades = load_trades()
    active = [t for t in trades if t["status"] == "ACTIVE"]
    closed = [t for t in trades if t["status"] == "CLOSED"]
    return {
        "active_trades": len(active), "closed_trades": len(closed),
        "realized_pnl": sum(t.get("realized_pnl", 0) for t in closed),
        "active_list": active
    }