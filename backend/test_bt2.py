import sys
import os
sys.path.append(os.getcwd())
import pandas as pd
from core.groww_client import GrowwClient
from services.backtest_service import _simulate_intraday_trades

try:
    print('Testing VWAP_RUNNER with GrowwClient fallback...')
    client = GrowwClient(api_key='', secret_key='', client_id='')
    raw = client.get_historical_intraday_data('RELIANCE.NS', '2023-10-01', '2023-10-15')
    if not raw:
        print('No raw data')
    else:
        df = pd.DataFrame(raw)
        for col in ['close', 'high', 'low', 'open', 'volume']:
            df[col] = pd.to_numeric(df.get(col, 0))
        df = df.dropna(subset=['close'])
        
        # Need to parse 'date' correctly if VWAP expects it
        market_data = {'RELIANCE.NS': df}
        trades = _simulate_intraday_trades(market_data, 100000, 1.0)
        print(f'Trades found: {len(trades)}')
        for t in trades[:5]:
            print(t)
except Exception as e:
    import traceback
    traceback.print_exc()
