import yfinance as yf
import requests

session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
})

print("Testing with custom session:")
try:
    ticker = yf.Ticker("TMCV.NS", session=session)
    df = ticker.history(start="2026-06-01", end="2026-06-14")
    print("Fetched data length:", len(df))
    if not df.empty:
        print(df.head())
except Exception as e:
    print("Error:", e)
