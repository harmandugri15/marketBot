import inspect
from growwapi import GrowwAPI

output = ""
try:
    output += "get_historical_candles signature:\n"
    output += str(inspect.signature(GrowwAPI.get_historical_candles)) + "\n\n"
except Exception as e:
    output += f"Error getting get_historical_candles signature: {e}\n\n"

try:
    output += "get_historical_candle_data signature:\n"
    output += str(inspect.signature(GrowwAPI.get_historical_candle_data)) + "\n\n"
except Exception as e:
    output += f"Error getting get_historical_candle_data signature: {e}\n\n"

with open("D:\\marketbot\\backend\\groww_signatures.txt", "w") as f:
    f.write(output)
