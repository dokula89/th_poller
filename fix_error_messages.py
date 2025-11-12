import re

# Read the file
with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace update_db_status calls to include error messages
# Pattern 1: Simple error calls
content = re.sub(
    r'update_db_status\("error"\)(\s+except Exception as e:)',
    r'update_db_status("error", str(e))\1',
    content
)

# Pattern 2: After exception handlers - add error parameter
replacements = [
    # Step 1 exceptions
    (r'(except Exception as e:.*?status_labels\[idx\].*Failed.*?finish_step_timer.*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", f"Step 1: {str(e)}")'),
    # Step 2 JSON not found
    (r'(error_msg = f"JSON file not found:.*?".*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", error_msg)'),
    # Step 2 No listings
    (r'(error_msg = f"No listings found in JSON".*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", error_msg)'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content, flags=re.DOTALL)

# Write back
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed error message passing")
