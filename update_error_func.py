import re

with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the function definition
in_function = False
new_lines = []
i = 0

while i < len(lines):
    line = lines[i]
    
    # Find the function definition
    if 'def update_db_status(new_status):' in line:
        new_lines.append(line.replace('def update_db_status(new_status):', 'def update_db_status(new_status, error_msg=None):'))
        in_function = True
    # Find the execute line
    elif in_function and 'cursor.execute(f"UPDATE {table} SET status = %s WHERE id = %s"' in line:
        # Replace with error_message support
        spaces = len(line) - len(line.lstrip())
        new_lines.append(' ' * spaces + 'if error_msg:\n')
        new_lines.append(' ' * (spaces + 4) + 'cursor.execute(f"UPDATE {table} SET status = %s, error_message = %s WHERE id = %s", (new_status, error_msg, step_target_id))\n')
        new_lines.append(' ' * spaces + 'else:\n')
        new_lines.append(' ' * (spaces + 4) + line)
        i += 1
        in_function = False
        continue
    else:
        new_lines.append(line)
    
    i += 1

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print('Updated update_db_status function')
