import os
from dotenv import load_dotenv
from growwapi import GrowwAPI
import json

load_dotenv("D:\\marketbot\\.env")
api_key = os.getenv("GROWW_API_KEY")
secret_key = os.getenv("GROWW_SECRET_KEY")

output = "=== Groww API Multi-Endpoint Test ===\n"
try:
    token = GrowwAPI.get_access_token(api_key=api_key, secret=secret_key)
    client = GrowwAPI(token)
    output += "Authentication successful!\n\n"
    
    # 1. Test profile
    try:
        prof = client.get_user_profile()
        output += f"1. Profile Success: {json.dumps(prof, indent=2)}\n\n"
    except Exception as e:
        output += f"1. Profile Failed: {e}\n\n"
        
    # 2. Test holdings
    try:
        holdings = client.get_holdings_for_user()
        output += f"2. Holdings Success: {json.dumps(holdings, indent=2)}\n\n"
    except Exception as e:
        output += f"2. Holdings Failed: {e}\n\n"
        
    # 3. Test positions
    try:
        positions = client.get_positions_for_user()
        output += f"3. Positions Success: {json.dumps(positions, indent=2)}\n\n"
    except Exception as e:
        output += f"3. Positions Failed: {e}\n\n"

    # 4. Test LTP
    try:
        ltp = client.get_ltp(segment="CASH", exchange_trading_symbols="NSE_ADANIENT")
        output += f"4. LTP Success: {json.dumps(ltp, indent=2)}\n\n"
    except Exception as e:
        output += f"4. LTP Failed: {e}\n\n"
        
except Exception as e:
    output += f"General Auth Error: {e}\n"

with open("D:\\marketbot\\backend\\groww_endpoint_test_results.txt", "w") as f:
    f.write(output)
