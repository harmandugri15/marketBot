with open("D:\\marketbot\\index.html", "r", encoding="utf-8") as f:
    content = f.read()

import re

# Find the loadBtResults function inside index.html
match = re.search(r"async\s+function\s+loadBtResults\s*\(.*?\)\s*\{([\s\S]*?)\n\s*\}", content)
if match:
    print("Found loadBtResults:")
    print("async function loadBtResults() {")
    print(match.group(1))
    print("}")
else:
    # Try finding it without async
    match2 = re.search(r"function\s+loadBtResults\s*\(.*?\)\s*\{([\s\S]*?)\n\s*\}", content)
    if match2:
        print("Found loadBtResults:")
        print("function loadBtResults() {")
        print(match2.group(1))
        print("}")
    else:
        print("Not found loadBtResults")
