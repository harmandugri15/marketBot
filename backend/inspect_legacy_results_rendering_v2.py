with open("D:\\marketbot\\index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

print("Printing lines 2140 to 2250 of legacy index.html:")
for i in range(2139, min(2250, len(lines))):
    print(f"{i+1}: {lines[i]}", end="")
