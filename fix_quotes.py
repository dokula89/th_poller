"""Fix all corrupted characters"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix corrupted quotes
fixes = [
    ('"', '"'),  # Curved quote to straight
    ('"', '"'),  # Other curved quote
    (''', "'"),  # Curved single quote
    (''', "'"),  # Other curved single quote
]

total = 0
for old, new in fixes:
    count = content.count(old)
    if count > 0:
        content = content.replace(old, new)
        total += count
        print(f'{old} -> {new}: {count}')

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'\n✅ Fixed {total} corrupted characters')
