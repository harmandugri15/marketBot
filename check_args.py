import inspect
from growwapi import GrowwAPI

print("=== EXACT ARGUMENTS FOR HISTORICAL DATA ===")
# This will print the exact parameter names the function expects
print(inspect.signature(GrowwAPI.get_historical_candles))