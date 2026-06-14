import os
from dotenv import load_dotenv
from growwapi import GrowwAPI
import json

# Load env variables from root folder
load_dotenv("D:\\marketbot\\.env")
api_key = os.getenv("GROWW_API_KEY")
secret_key = os.getenv("GROWW_SECRET_KEY")

output = ""
try:
    output += f"Keys loaded: API_KEY={api_key[:15]}... | SECRET_KEY={secret_key[:5]}...\n"
    
    # Authenticate
    token = GrowwAPI.get_access_token(api_key=api_key, secret=secret_key)
    client = GrowwAPI(token)
    output += "Authentication successful!\n"
    
    # Try fetching historical candles for ADANIENT
    res = client.get_historical_candles(
        exchange="NSE",
        segment="CASH",
        groww_symbol="ADANIENT",
        start_time="2026-06-01 00:00:00",
        end_time="2026-06-14 23:59:59",
        candle_interval="1day"
    )
    
    output += "get_historical_candles response:\n"
    output += json.dumps(res, indent=2)
except Exception as e:
    output += f"Error: {e}\n"

with open("D:\\marketbot\\backend\\groww_test_historical_results.txt", "w") as f:
    f.write(output)
