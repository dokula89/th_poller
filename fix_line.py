#!/usr/bin/env python3
# Fix specific lines with corrupted characters

with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 821 (index 820) - the cols definition
lines[820] = '        cols = ("ID", "Link", "Int", "Last", "Next", "Status", "Δ$", "+", "-", "Total", "✏️", "hidden1", "hidden2")\n'

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed line 821')
