from growwapi import GrowwAPI

attrs = [
    "CANDLE_INTERVAL_DAY",
    "CANDLE_INTERVAL_HOUR_1",
    "CANDLE_INTERVAL_MIN_1",
    "CANDLE_INTERVAL_MIN_5",
    "CANDLE_INTERVAL_MIN_15",
]

output = ""
for attr in attrs:
    if hasattr(GrowwAPI, attr):
        val = getattr(GrowwAPI, attr)
        output += f"GrowwAPI.{attr} = {repr(val)} (type: {type(val)})\n"
    else:
        output += f"GrowwAPI.{attr} is NOT defined\n"

with open("D:\\marketbot\\backend\\groww_constants.txt", "w") as f:
    f.write(output)
