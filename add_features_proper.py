#!/usr/bin/env python3
"""
Properly restore ALL features with correct indentation
"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where to add the standalone function (before class)
class_line = None
for i, line in enumerate(lines):
    if line.strip().startswith('class OldCompactHUD'):
        class_line = i
        break

if class_line:
    # Insert update_db_status function before the class
    func_lines = [
        '\n',
        'def update_db_status(network_id, status, error_msg=None):\n',
        '    """Update network status in database with optional error message"""\n',
        '    try:\n',
        '        import mysql.connector\n',
        '        from config_auth import DB_CONFIG\n',
        '        \n',
        '        conn = mysql.connector.connect(**DB_CONFIG)\n',
        '        cursor = conn.cursor()\n',
        '        \n',
        '        if error_msg:\n',
        '            cursor.execute(\n',
        '                "UPDATE networks SET status = %s, error_message = %s WHERE id = %s",\n',
        '                (status, error_msg, network_id)\n',
        '            )\n',
        '        else:\n',
        '            cursor.execute(\n',
        '                "UPDATE networks SET status = %s, error_message = NULL WHERE id = %s",\n',
        '                (status, network_id)\n',
        '            )\n',
        '        \n',
        '        conn.commit()\n',
        '        cursor.close()\n',
        '        conn.close()\n',
        '    except Exception as e:\n',
        '        print(f"DB update error: {e}")\n',
        '\n',
    ]
    
    lines = lines[:class_line] + func_lines + lines[class_line:]
    print(f"✓ Added update_db_status function before class at line {class_line}")
    
    # Update class_line index after insertion
    class_line += len(func_lines)

# Find __init__ method and add tooltip dictionary
init_found = False
for i, line in enumerate(lines):
    if 'def __init__(self, opacity' in line:
        # Find the end of __init__ (next method definition)
        for j in range(i+1, len(lines)):
            if lines[j].strip().startswith('def ') and not lines[j].strip().startswith('def __'):
                # Insert before next method
                lines.insert(j, '        self._cell_tooltips = {}  # Store error tooltips\n')
                lines.insert(j+1, '\n')
                print(f"✓ Added tooltip dictionary at line {j}")
                init_found = True
                break
        break

if not init_found:
    print("⚠ Could not find __init__ method")

# Save
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Basic structure added successfully")
print("Next: Add workflow error handlers manually")
