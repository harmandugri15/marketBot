from growwapi import GrowwAPI

print("=== GROWW API AVAILABLE COMMANDS ===")
# This looks inside the package and lists every single command it knows
methods = [func for func in dir(GrowwAPI) if callable(getattr(GrowwAPI, func)) and not func.startswith("__")]

for method in methods:
    print(f" -> {method}")