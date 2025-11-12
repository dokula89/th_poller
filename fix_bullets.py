"""Fix corrupted bullet character"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace corrupted bullet
count = content.count('¢')
content = content.replace('¢', '•')

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'✅ Fixed {count} corrupted bullet characters')
