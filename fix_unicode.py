"""Fix corrupted Unicode characters in config_hud.py"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix corrupted play button
content = content.replace('â–¶', '▶')

# Fix corrupted pencil emoji
content = content.replace('âœï¸', '✏️')

# Fix other common corrupted characters
content = content.replace('âœ"', '✓')
content = content.replace('âŒ', '❌')
content = content.replace('â±ï¸', '⏱️')
content = content.replace('âœ…', '✅')

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('✅ Fixed corrupted Unicode characters')
