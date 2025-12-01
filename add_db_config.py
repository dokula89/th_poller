"""
Add module-level DB_CONFIG to config_hud_db.py
"""

with open('config_hud_db.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the docstring end and insert DB_CONFIG after it
for i, line in enumerate(lines):
    if line.strip() == '"""' and i > 2:  # This is the closing docstring
        # Insert DB_CONFIG after the docstring
        db_config_lines = [
            '\n',
            '# Database configuration - used by parcel automation\n',
            'DB_CONFIG = {\n',
            "    'host': 'localhost',\n",
            "    'port': 3306,\n",
            "    'user': 'root',\n",
            "    'password': '',\n",
            "    'database': 'offta'\n",
            '}\n',
            '\n',
        ]
        
        # Insert after the closing docstring
        for idx, db_line in enumerate(db_config_lines):
            lines.insert(i + 1 + idx, db_line)
        
        print(f"✓ Added DB_CONFIG at line {i+2}")
        break

with open('config_hud_db.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Module-level DB_CONFIG added to config_hud_db.py")
