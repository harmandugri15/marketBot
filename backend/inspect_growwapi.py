import sys
import os

try:
    from growwapi import GrowwAPI
    
    methods = [m for m in dir(GrowwAPI) if not m.startswith('_')]
    output = f"GrowwAPI methods:\n" + "\n".join(methods)
except Exception as e:
    output = f"Error: {e}"

with open("D:\\marketbot\\backend\\groww_inspect_results.txt", "w") as f:
    f.write(output)
