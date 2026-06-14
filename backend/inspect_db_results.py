from database import SessionLocal
from models.backtest_result import BacktestResult
import json

db = SessionLocal()
try:
    results = db.query(BacktestResult).order_by(BacktestResult.id.desc()).all()
    print(f"Total Backtest Results: {len(results)}")
    for r in results:
        print(f"ID: {r.id} | Strategy: {r.strategy} | Run Date: {r.run_date}")
        print(f"  Period: {r.start_date} -> {r.end_date}")
        print(f"  Initial Capital: {r.initial_capital} | Final Capital: {r.final_capital} | Return: {r.total_return_pct}%")
        print(f"  Win Rate: {r.win_rate}% | Total Trades: {r.total_trades}")
        print(f"  Trade Log Count: {len(r.trade_log) if r.trade_log else 0}")
        print(f"  Equity Curve Count: {len(r.equity_curve) if r.equity_curve else 0}")
        if r.trade_log:
            print("  Sample Trades:")
            for t in r.trade_log[:3]:
                print(f"    {t.get('symbol')}: {t.get('entry_date')} (Entry: {t.get('entry')}) -> {t.get('exit_date')} (Exit: {t.get('exit')}) | PnL: {t.get('pnl')}")
        print("=" * 80)
finally:
    db.close()
