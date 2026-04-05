"""
app.py — Flask web server. Run with: python app.py
Then open: http://localhost:5000
"""

import os
import sys
import json
import logging
import threading
import time
from datetime import datetime

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Windows Unicode fix
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_fh  = logging.FileHandler("logs/bot.log", encoding="utf-8")
_fh.setFormatter(logging.Formatter(_fmt))
_sh  = logging.StreamHandler(sys.stdout)
_sh.setFormatter(logging.Formatter(_fmt))
if sys.platform == "win32":
    try:
        _sh.stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, handlers=[_fh, _sh])
logger = logging.getLogger(__name__)

from config import (
    TRADING_CAPITAL, RISK_PER_TRADE_PCT, MAX_STOP_LOSS_PCT,
    PAPER_TRADING, STOCK_UNIVERSE, BACKTEST_START_DATE, BACKTEST_END_DATE
)
from groww_api    import GrowwAPI
from scanner      import run_scan, load_signals
from backtester   import run_backtest, load_backtest_results
from trade_manager import open_trade, get_active_trades, get_all_trades, get_portfolio_summary
import forward_test as ft

app = Flask(__name__)
CORS(app)
api = GrowwAPI()

backtest_progress = {"running": False, "current": 0, "total": 0, "symbol": "", "done": False, "error": None}
scan_progress     = {"running": False, "current": 0, "total": 0, "symbol": "", "done": False, "error": None}


# ── Pages ─────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── Status ────────────────────────────────────────────────────────────────────
@app.route("/api/status")
def api_status():
    from config import GROWW_API_KEY
    api_configured = bool(GROWW_API_KEY and GROWW_API_KEY != "your_api_key_here")
    data_ok        = api.test_connection()
    groww_ok       = False
    if api_configured:
        try:
            api.get_funds()
            groww_ok = True
        except Exception:
            pass

    return jsonify({
        "api_configured":  api_configured,
        "api_connected":   data_ok,
        "groww_connected": groww_ok,
        "paper_trading":   PAPER_TRADING,
        "market_open":     api.is_market_open(),
        "capital":         TRADING_CAPITAL,
        "risk_pct":        RISK_PER_TRADE_PCT,
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })


# ── Config ────────────────────────────────────────────────────────────────────
@app.route("/api/config", methods=["GET", "POST"])
def config_endpoint():
    if request.method == "GET":
        return jsonify({
            "capital":       TRADING_CAPITAL,
            "risk_pct":      RISK_PER_TRADE_PCT,
            "max_sl_pct":    MAX_STOP_LOSS_PCT,
            "paper_trading": PAPER_TRADING,
        })

    data     = request.json or {}
    env_path = ".env"
    lines    = open(env_path).readlines() if os.path.exists(env_path) else []
    updates  = {
        "GROWW_API_KEY":      data.get("api_key", ""),
        "GROWW_SECRET_KEY":   data.get("secret_key", ""),
        "GROWW_CLIENT_ID":    data.get("client_id", ""),
        "TRADING_CAPITAL":    str(data.get("capital", TRADING_CAPITAL)),
        "RISK_PER_TRADE_PCT": str(data.get("risk_pct", RISK_PER_TRADE_PCT)),
        "MAX_STOP_LOSS_PCT":  str(data.get("max_sl_pct", MAX_STOP_LOSS_PCT)),
        "PAPER_TRADING":      "TRUE" if data.get("paper_trading", True) else "FALSE",
    }
    done = set()
    new_lines = []
    for line in lines:
        key = line.split("=")[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            done.add(key)
        else:
            new_lines.append(line)
    for k, v in updates.items():
        if k not in done and v:
            new_lines.append(f"{k}={v}\n")
    with open(env_path, "w") as f:
        f.writelines(new_lines)
    return jsonify({"success": True, "message": "Saved. Restart bot to apply API key changes."})


# ── Scanner ───────────────────────────────────────────────────────────────────
@app.route("/api/scan/run", methods=["POST"])
def start_scan():
    global scan_progress
    if scan_progress["running"]:
        return jsonify({"error": "Scan already running"}), 400

    data     = request.json or {}
    strategy = data.get("strategy", "DEP")
    scan_progress = {"running": True, "current": 0, "total": len(STOCK_UNIVERSE),
                     "symbol": "", "done": False, "error": None}

    def _cb(current, total, symbol):
        scan_progress["current"] = current
        scan_progress["total"]   = total
        scan_progress["symbol"]  = symbol

    def _run():
        global scan_progress
        try:
            run_scan(api, progress_callback=_cb, strategy=strategy)
            scan_progress.update({"done": True, "running": False})
        except Exception as e:
            logger.error(f"Scan failed: {e}")
            scan_progress.update({"done": True, "running": False, "error": str(e)})

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True})


@app.route("/api/scan/progress")
def scan_progress_ep():
    return jsonify(scan_progress)


@app.route("/api/scan/signals")
def get_signals():
    return jsonify(load_signals())


# ── Backtest ──────────────────────────────────────────────────────────────────
@app.route("/api/backtest/run", methods=["POST"])
def start_backtest():
    global backtest_progress
    if backtest_progress["running"]:
        return jsonify({"error": "Backtest already running"}), 400

    data     = request.json or {}
    start    = data.get("start_date", BACKTEST_START_DATE)
    end      = data.get("end_date",   BACKTEST_END_DATE)
    capital  = float(data.get("capital", TRADING_CAPITAL))
    strategy = data.get("strategy", "DEP")
    count    = data.get("symbols_count", None)
    symbols  = STOCK_UNIVERSE[:int(count)] if count else STOCK_UNIVERSE

    backtest_progress = {"running": True, "current": 0, "total": len(symbols),
                         "symbol": "", "done": False, "error": None}

    def _cb(cur, tot, sym):
        backtest_progress["current"] = cur
        backtest_progress["total"]   = tot
        backtest_progress["symbol"]  = sym

    def _run():
        global backtest_progress
        try:
            run_backtest(api, start, end, capital, symbols, _cb, strategy)
            backtest_progress.update({"done": True, "running": False})
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            backtest_progress.update({"done": True, "running": False, "error": str(e)})

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True})


@app.route("/api/backtest/progress")
def bt_progress():
    return jsonify(backtest_progress)


@app.route("/api/backtest/results")
def bt_results():
    r = load_backtest_results()
    if not r:
        return jsonify({"error": "No backtest results yet."}), 404
    return jsonify(r)


# ── Forward Test (server-side, survives refresh) ──────────────────────────────
@app.route("/api/forward/summary")
def ft_summary():
    return jsonify(ft.get_summary())


@app.route("/api/forward/add", methods=["POST"])
def ft_add():
    signal = request.json
    if not signal:
        return jsonify({"error": "No signal provided"}), 400
    try:
        trade = ft.add_trade(signal)
        return jsonify({"success": True, "trade": trade})
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/forward/enter", methods=["POST"])
def ft_enter():
    data     = request.json or {}
    trade_id = data.get("trade_id")
    price    = data.get("actual_entry_price")
    if not trade_id:
        return jsonify({"error": "trade_id required"}), 400
    try:
        trade = ft.mark_entered(trade_id, price)
        return jsonify({"success": True, "trade": trade})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/forward/close", methods=["POST"])
def ft_close():
    data      = request.json or {}
    trade_id  = data.get("trade_id")
    exit_px   = data.get("exit_price")
    reason    = data.get("exit_reason", "Manual Exit")
    if not trade_id or exit_px is None:
        return jsonify({"error": "trade_id and exit_price required"}), 400
    try:
        trade = ft.close_trade(trade_id, float(exit_px), reason)
        return jsonify({"success": True, "trade": trade})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/forward/delete", methods=["POST"])
def ft_delete():
    data     = request.json or {}
    trade_id = data.get("trade_id")
    if not trade_id:
        return jsonify({"error": "trade_id required"}), 400
    ok = ft.delete_trade(trade_id)
    return jsonify({"success": ok})


# ── Trades (paper/live) ───────────────────────────────────────────────────────
@app.route("/api/trades/summary")
def trade_summary():
    return jsonify(get_portfolio_summary())


@app.route("/api/trades/open", methods=["POST"])
def open_trade_ep():
    signal = request.json
    if not signal:
        return jsonify({"error": "No signal"}), 400
    try:
        trade = open_trade(api, signal)
        return jsonify({"success": True, "trade": trade})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Logs ──────────────────────────────────────────────────────────────────────
@app.route("/api/logs")
def get_logs():
    try:
        with open("logs/bot.log", encoding="utf-8") as f:
            lines = f.readlines()
        return jsonify({"lines": lines[-150:]})
    except Exception:
        return jsonify({"lines": []})


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("VCP Trading Bot starting")
    logger.info(f"Mode:    {'PAPER' if PAPER_TRADING else 'LIVE'}")
    logger.info(f"Capital: Rs {TRADING_CAPITAL:,.0f}")
    logger.info(f"Risk:    {RISK_PER_TRADE_PCT}% per trade")
    logger.info("Dashboard: http://localhost:5000")
    logger.info("=" * 60)
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)