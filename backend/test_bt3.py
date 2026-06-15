import sys
import os
sys.path.append(os.getcwd())
import pandas as pd
from core.groww_client import GrowwClient
from services.backtest_service import _simulate_swing_trades, _build_indicators
from datetime import datetime

try:
    print('Testing HARMAN1_PULLBACK with GrowwClient fallback...')
    client = GrowwClient(api_key='', secret_key='', client_id='')
    raw = client.get_historical_data('RELIANCE.NS', '2023-01-01', '2024-01-01')
    if not raw:
        print('No raw data')
    else:
        df = pd.DataFrame(raw)
        for col in ['close', 'high', 'low', 'open', 'volume']:
            df[col] = pd.to_numeric(df.get(col, 0))
        df = df.dropna(subset=['close'])
        df = _build_indicators(df)
        df['date_idx'] = pd.to_datetime(df['date']).dt.date
        df = df.set_index('date_idx')
        market_data = {'RELIANCE.NS': df}
        trades = _simulate_swing_trades(market_data, datetime(2023, 5, 1).date(), datetime(2023, 12, 1).date(), 100000, 1.0)
        print(f'Trades found: {len(trades)}')
        for t in trades[:5]:
            print(t)
except Exception as e:
    import traceback
    traceback.print_exc()
