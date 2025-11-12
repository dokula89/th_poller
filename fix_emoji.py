#!/usr/bin/env python3
# Fix specific emoji and character issues

with open('config_hud.py', 'rb') as f:
    content = f.read()

# Fix corrupted pencil emoji (✏️ = \xe2\x9c\x8f\xef\xb8\x8f but may be corrupted)
# Fix corrupted delta (Δ may be showing as Î")

replacements = [
    (b'\xc3\x8e\xe2\x80\x9c', b'\xce\x94'),  # Corrupted Δ to proper Δ  
    (b'\xe2\x9c\x8f\xc3\xaf\xc2\xb8\xe2\x80\x8f', b'\xe2\x9c\x8f\xef\xb8\x8f'),  # Corrupted pencil to proper ✏️
]

count = 0
for old, new in replacements:
    before = content.count(old)
    content = content.replace(old, new)
    if before > 0:
        count += before
        print(f'Replaced {before} occurrences of corrupted byte sequence')

with open('config_hud.py', 'wb') as f:
    f.write(content)

print(f'\nTotal replacements: {count}')
