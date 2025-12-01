"""Quick fix for the syntax error"""

# Read file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the escaped quotes issue - replace \' with just '
content = content.replace("DB_CONFIG.get(\\'host\\', \\'unknown\\')", "DB_CONFIG.get('host', 'unknown')")

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed syntax error")
