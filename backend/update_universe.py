import sys
import os
import requests
import pandas as pd
import re

url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
try:
    df = pd.read_csv(url)
    symbols = df['Symbol'].tolist()
    symbols = [s + ".NS" for s in symbols]
    
    config_path = "D:/marketbot/backend/config.py"
    with open(config_path, "r") as f:
        content = f.read()
    
    # Replace STOCK_UNIVERSE = [...] with the new list
    formatted_list = '[\n    ' + ',\n    '.join(['"' + s + '"' for s in symbols]) + '\n]'
    new_content = re.sub(r'STOCK_UNIVERSE\s*=\s*\[.*?\]', f'STOCK_UNIVERSE = {formatted_list}', content, flags=re.DOTALL)
    
    with open(config_path, "w") as f:
        f.write(new_content)
        
    print(f"Updated STOCK_UNIVERSE with {len(symbols)} symbols from Nifty 500.")
except Exception as e:
    import traceback
    traceback.print_exc()
