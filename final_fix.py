with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Simple string replacement - replace all occurrences
count = content.count('Î"')
content = content.replace('Î"', 'Δ')
print(f'Replaced {count} corrupted Delta symbols')

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
