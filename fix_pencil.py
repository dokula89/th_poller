with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all occurrences of corrupted pencil emoji
count = content.count('✏"')
content = content.replace('✏"', '✏️')
print(f'Replaced {count} corrupted pencil emoji')

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
