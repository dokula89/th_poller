#!/usr/bin/env python3
"""
Comprehensive fix for config_utils.py indentation and function order issues.
"""

def fix_config_utils():
    filepath = r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix 1: Move _refresh_status_counts before _refresh_queue_table
    # Extract the function (it's around line 4772-4878 in backup)
    # Find it by searching for the function definition and assignment
    import re
    
    # Find _refresh_status_counts function
    pattern_start = r'(\n\s{8}# Function to refresh status counts from API\n\s{8}def _refresh_status_counts\(silent: bool = False\):)'
    pattern_end = r'(\s{4}self\._refresh_status_counts = _refresh_status_counts\n)'
    
    match_start = re.search(pattern_start, content)
    match_end = re.search(pattern_end, content)
    
    if match_start and match_end:
        # Extract the function
        func_start = match_start.start()
        func_end = match_end.end()
        func_content = content[func_start:func_end]
        
        # Remove from current location
        content = content[:func_start] + content[func_end:]
        
        # Find where to insert (before _refresh_queue_table)
        insert_pattern = r'(\n\s{8}# Define _refresh_queue_table function\n\s{8}def _refresh_queue_table\(silent: bool = False\):)'
        insert_match = re.search(insert_pattern, content)
        
        if insert_match:
            # Insert before _refresh_queue_table
            insert_pos = insert_match.start()
            content = content[:insert_pos] + func_content + content[insert_pos:]
            print("✓ Moved _refresh_status_counts before _refresh_queue_table")
    
    # Write back
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✓ All fixes applied!")

if __name__ == "__main__":
    fix_config_utils()
