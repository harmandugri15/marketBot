with open("D:\\marketbot\\index.html", "r", encoding="utf-8") as f:
    content = f.read()

import re

# Find javascript functions related to backtest
functions = re.findall(r"function\s+[a-zA-Z0-9_]+\s*\(.*?\)\s*\{[^{}]*\}", content)
backtest_funcs = [f for f in functions if "backtest" in f.lower()]

print("Found backtest related functions:")
for bf in backtest_funcs[:10]:
    print(bf)
    print("-" * 40)

# Let's search for "backtest" and print some surrounding lines
lines = content.split("\n")
matches = [i for i, l in enumerate(lines) if "backtest" in l.lower()]
print(f"Total occurrences of 'backtest': {len(matches)}")

with open("D:\\marketbot\\backend\\legacy_backtest_code.txt", "w", encoding="utf-8") as out:
    for idx in matches:
        start = max(0, idx - 5)
        end = min(len(lines), idx + 6)
        out.write(f"--- Line {idx} ---\n")
        out.write("\n".join(lines[start:end]))
        out.write("\n" + "="*80 + "\n")
