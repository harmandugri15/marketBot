import sys
import os
sys.path.append(os.getcwd())
import pandas as pd
import yfinance as yf
from services.backtest_service import _build_indicators, _simulate_vcp_trades

try:
    print('Downloading data...')
    ticker = yf.Ticker('RELIANCE.NS')
    df = ticker.history(start='2022-01-01', end='2024-01-01')
    if df.empty:
        print('No raw data')
    else:
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        df = df.rename(columns={'date': 'date'})
        df = df.set_index('date')
        for col in ['close', 'high', 'low', 'open', 'volume']:
            df[col] = pd.to_numeric(df.get(col, 0))
        df = df.dropna(subset=['close'])
        df = _build_indicators(df)
        trades = _simulate_vcp_trades(df, 'RELIANCE.NS', 100000, 1.0, 12.0)
        print(f'Trades found: {len(trades)}')
        for t in trades[:5]:
            print(t)
except Exception as e:
    import traceback
    traceback.print_exc()
