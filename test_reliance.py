import os
from dotenv import load_dotenv
from growwapi import GrowwAPI

load_dotenv()
api_key = os.getenv("GROWW_API_KEY")
secret = os.getenv("GROWW_SECRET_KEY")

print("=== GROWW API SURGICAL TEST V2 ===")

try:
    print("⏳ Authenticating...")
    # FIXED: Explicitly naming the keyword arguments!
    token = GrowwAPI.get_access_token(api_key=api_key, secret=secret)
    client = GrowwAPI(token)
    print("✅ Authenticated.\n")

    print("1️⃣ Looking up RELIANCE in Groww's internal database...")
    instrument = client.get_instrument_by_exchange_and_trading_symbol("NSE", "RELIANCE")
    print(f"Dictionary Result: {instrument}\n")

    # Safely extract whatever token/name Groww uses internally
    true_symbol = instrument.get("groww_symbol", "RELIANCE") if isinstance(instrument, dict) else "RELIANCE"

    print(f"2️⃣ Attempting to fetch Historical Data using true symbol: {true_symbol} ...")
    data = client.get_historical_candles(
        exchange="NSE",
        segment="CASH",
        groww_symbol=true_symbol,
        start_time="2024-01-01",
        end_time="2024-01-05",
        candle_interval="1D"
    )
    print("\n🎉 SUCCESS! Data fetched:")
    print(data)

except Exception as e:
    print(f"\n❌ RAW ERROR TRIGGERED: {type(e).__name__} - {e}")
    if hasattr(e, 'response') and e.response is not None:
        print(f"🚨 Groww Server Message: {e.response.text}")