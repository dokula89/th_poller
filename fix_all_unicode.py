#!/usr/bin/env python3
# Fix all corrupted Δ and pencil emoji

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace corrupted characters
replacements = {
    'Î"': 'Δ',      # Corrupted delta
    '✏ï¸': '✏️',    # Corrupted pencil emoji
    ''¾': ' ',      # Corrupted space
    '"•': ' • ',    # Corrupted bullet with quotes
    ''': "'",       # Another smart quote variant
}

count = 0
for old, new in replacements.items():
    before = content.count(old)
    if before > 0:
        content = content.replace(old, new)
        count += before
        print(f'Replaced {before} occurrences of {repr(old)} with {repr(new)}')

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\nTotal replacements: {count}')
