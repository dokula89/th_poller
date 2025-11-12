import re

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix corrupted flag emoji - replace 🏁" followed by any non-quote character with just 🏁 
count1 = len(re.findall(r'🏁"[^"]', content))
content = re.sub(r'🏁"([^"])', r'🏁 \1', content)
print(f'Fixed {count1} corrupted flag emoji')

# Also fix the standalone case like "🏁"ž" -> "🏁"  
count2 = content.count('"🏁"§"')
content = content.replace('"🏁"§"', '"🏁📧"')
print(f'Fixed {count2} email emoji')

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Done!')
