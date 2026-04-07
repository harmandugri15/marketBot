import os
import sys
import json
import logging
import threading
import time
from datetime import datetime

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS

# Windows Terminal Fixes
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

# Logging Configuration
_fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, 
                    handlers=[logging.FileHandler("logs/bot.log", encoding="utf-8"),
                              logging.StreamHandler(sys.stdout)],
                    format=_fmt)
logger = logging.getLogger(__name__)

# Dynamic Imports
from config import (
    STOCK_UNIVERSE, BACKTEST_START_DATE, BACKTEST_END_DATE,
    get_settings, save_settings, GROWW_API_KEY
)
from groww_api     import GrowwAPI
from scanner       import run_scan, load_signals
from backtester    import run_backtest, load_backtest_results
from trade_manager import open_trade, get_portfolio_summary
import forward_test as ft

app = Flask(__name__, template_folder='.', static_folder='data')
CORS(app)
api = GrowwAPI()

# Global Progress State
bt_state = {"running": False, "current": 0, "total": 0, "symbol": "", "done": False, "error": None}
sc_state = {"running": False, "current": 0, "total": 0, "symbol": "", "done": False, "error": None}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/status")
def api_status():
    settings = get_settings()
    return jsonify({
        "api_configured":  bool(GROWW_API_KEY),
        "api_connected":   api.test_connection(),
        "groww_connected": False, # Add session check if needed
        "paper_trading":   settings.get("paper_trading", True),
        "market_open":     api.is_market_open(),
        "capital":         settings.get("capital", 2000),
        "risk_pct":        settings.get("risk_pct", 5.0),
        "timestamp":       datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

@app.route("/api/config", methods=["GET", "POST"])
def config_endpoint():
    if request.method == "GET": return jsonify(get_settings())
    data = request.json or {}
    try:
        updated = save_settings(data)
        return jsonify({"success": True, "message": "Settings updated!", "settings": updated})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/scan/run", methods=["POST"])
def start_scan():
    global sc_state
    if sc_state["running"]: return jsonify({"error": "Already running"}), 400
    
    data = request.json or {}
    sc_state = {"running": True, "current": 0, "total": len(STOCK_UNIVERSE), "symbol": "", "done": False, "error": None}
    
    def _run():
        try:
            run_scan(api, progress_callback=lambda c,t,s: sc_state.update({"current":c, "total":t, "symbol":s}), strategy=data.get("strategy", "AUTO"))
            sc_state.update({"done": True, "running": False})
        except Exception as e: sc_state.update({"done": True, "running": False, "error": str(e)})

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True})

@app.route("/api/scan/progress")
def scan_progress_ep(): return jsonify(sc_state)

@app.route("/api/scan/signals")
def get_signals(): return jsonify(load_signals())

@app.route("/api/backtest/run", methods=["POST"])
def start_backtest():
    global bt_state
    if bt_state["running"]: return jsonify({"error": "Already running"}), 400
    
    settings = get_settings()
    data = request.json or {}
    count = data.get("symbols_count")
    symbols = STOCK_UNIVERSE[:int(count)] if count else STOCK_UNIVERSE
    
    bt_state = {"running": True, "current": 0, "total": len(symbols), "symbol": "", "done": False, "error": None}

    def _run():
        try:
            run_backtest(api, data.get("start_date"), data.get("end_date"), 
                         float(data.get("capital", settings["capital"])), 
                         symbols, lambda c,t,s: bt_state.update({"current":c, "total":t, "symbol":s}), 
                         data.get("strategy", "AUTO"))
            bt_state.update({"done": True, "running": False})
        except Exception as e: bt_state.update({"done": True, "running": False, "error": str(e)})

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"started": True})

@app.route("/api/backtest/progress")
def bt_progress(): return jsonify(bt_state)

@app.route("/api/backtest/results")
def bt_results():
    r = load_backtest_results()
    return jsonify(r) if r else (jsonify({"error": "No data"}), 404)

@app.route("/api/forward/summary")
def ft_summary(): return jsonify(ft.get_summary())

@app.route("/api/forward/add", methods=["POST"])
def ft_add():
    try: return jsonify({"success": True, "trade": ft.add_trade(request.json)})
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route("/api/forward/enter", methods=["POST"])
def ft_enter():
    d = request.json
    try: return jsonify({"success": True, "trade": ft.mark_entered(d['trade_id'], d.get('actual_entry_price'))})
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route("/api/forward/close", methods=["POST"])
def ft_close():
    d = request.json
    try: return jsonify({"success": True, "trade": ft.close_trade(d['trade_id'], float(d['exit_price']), d.get('exit_reason'))})
    except Exception as e: return jsonify({"error": str(e)}), 400

@app.route("/api/forward/delete", methods=["POST"])
def ft_delete():
    return jsonify({"success": ft.delete_trade(request.json.get('trade_id'))})

@app.route("/api/trades/summary")
def trade_summary(): return jsonify(get_portfolio_summary())

@app.route("/api/trades/open", methods=["POST"])
def open_trade_ep():
    try: return jsonify({"success": True, "trade": open_trade(api, request.json)})
    except Exception as e: return jsonify({"error": str(e)}), 500

@app.route("/api/logs")
def get_logs():
    try:
        with open("logs/bot.log", "r", encoding="utf-8") as f: lines = f.readlines()
        return jsonify({"lines": lines[-100:]})
    except: return jsonify({"lines": []})

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000, use_reloader=False)