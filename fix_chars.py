#!/usr/bin/env python3
# Simple character replacement script

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = {
    '\u201c': '"',  # Smart quote left
    '\u201d': '"',  # Smart quote right
    '\u2018': "'",  # Single quote left
    '\u2019': "'",  # Single quote right
    '\u201e': '"',  # Double low-9 quote
    '\u201a': "'",  # Single low-9 quote
    '\u0160': '"',  # S with caron
    '\u2022': '•',  # Bullet
    '\u0153': ' ',  # oe ligature (corrupted space)
    '\u00a0': ' ',  # non-breaking space
    '\u2013': '-',  # en dash
    '\u2014': '-',  # em dash
}

count = 0
for old, new in replacements.items():
    before = content.count(old)
    content = content.replace(old, new)
    if before > 0:
        count += before
        print(f'Replaced {before} occurrences of U+{ord(old):04X} with {repr(new)}')

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nTotal replacements: {count}')
