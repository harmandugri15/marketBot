import yfinance as yf
import os

temp_cache_dir = os.path.abspath("temp_py_yfinance_cache")
os.makedirs(temp_cache_dir, exist_ok=True)
yf.cache.set_cache_location(temp_cache_dir)

print("Testing with fresh cache location:", temp_cache_dir)
try:
    ticker = yf.Ticker("TMCV.NS")
    df = ticker.history(start="2026-06-01", end="2026-06-14")
    print("Fetched data length:", len(df))
    if not df.empty:
        print(df.head())
except Exception as e:
    print("Error:", e)
