import re

# Read the file
with open(r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py", "r", encoding="utf-8") as f:
    content = f.read()

# Fix the indentation issue - remove 4 spaces from lines 829-837
lines = content.split("\n")

# Lines 829-837 (0-indexed: 828-836)
for i in range(828, 837):
    if i < len(lines) and lines[i].startswith("                    "):
        # Remove 4 spaces from the beginning
        lines[i] = lines[i][4:]

# Write back
with open(r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py", "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("Fixed indentation!")
