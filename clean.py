import json

# 1. Load the corrupted database
with open('data/forward_test.json', 'r') as f:
    db = json.load(f)

print(f"Total trades before cleanup: {len(db['trades'])}")

# 2. Filter out duplicates (keeps only the first instance of each symbol)
seen_symbols = set()
unique_trades = []

for t in db['trades']:
    if t['symbol'] not in seen_symbols:
        unique_trades.append(t)
        seen_symbols.add(t['symbol'])

db['trades'] = unique_trades

# 3. Save the clean database
with open('data/forward_test.json', 'w') as f:
    json.dump(db, f, indent=2)

print(f"✅ Cleaned! Database reduced to {len(unique_trades)} unique trades.")