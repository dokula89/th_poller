#!/usr/bin/env python3
"""
Add error tracking to all workflow error handlers
"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

changes = 0

# Find all error handlers and add update_db_status calls
for i, line in enumerate(lines):
    # Look for patterns like "Step X failed:" in error messages
    if 'Step 1 failed:' in line and 'log_activity' in line:
        # Add update_db_status call after this line
        indent = len(line) - len(line.lstrip())
        new_line = ' ' * indent + 'update_db_status(job_data.get("network_id"), "error", str(e))\n'
        lines.insert(i+1, new_line)
        changes += 1
        print(f"✓ Added error tracking for Step 1 at line {i+1}")
    
    elif 'Step 2 failed:' in line and 'log_activity' in line:
        indent = len(line) - len(line.lstrip())
        new_line = ' ' * indent + 'update_db_status(job_data.get("network_id"), "error", str(e))\n'
        lines.insert(i+1, new_line)
        changes += 1
        print(f"✓ Added error tracking for Step 2 at line {i+1}")
    
    elif 'Step 3 failed:' in line and 'log_activity' in line:
        indent = len(line) - len(line.lstrip())
        new_line = ' ' * indent + 'update_db_status(job_data.get("network_id"), "error", str(e))\n'
        lines.insert(i+1, new_line)
        changes += 1
        print(f"✓ Added error tracking for Step 3 at line {i+1}")
    
    elif 'Step 4 failed:' in line and 'log_activity' in line:
        indent = len(line) - len(line.lstrip())
        new_line = ' ' * indent + 'update_db_status(job_data.get("network_id"), "error", str(e))\n'
        lines.insert(i+1, new_line)
        changes += 1
        print(f"✓ Added error tracking for Step 4 at line {i+1}")
    
    elif 'Step 5 failed:' in line and 'log_activity' in line:
        indent = len(line) - len(line.lstrip())
        new_line = ' ' * indent + 'update_db_status(job_data.get("network_id"), "error", str(e))\n'
        lines.insert(i+1, new_line)
        changes += 1
        print(f"✓ Added error tracking for Step 5 at line {i+1}")
    
    elif 'Step 6 failed:' in line and 'log_activity' in line:
        indent = len(line) - len(line.lstrip())
        new_line = ' ' * indent + 'update_db_status(job_data.get("network_id"), "error", str(e))\n'
        lines.insert(i+1, new_line)
        changes += 1
        print(f"✓ Added error tracking for Step 6 at line {i+1}")

# Save
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\n✓ Added {changes} error tracking calls")
