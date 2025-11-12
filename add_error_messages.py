"""Update all update_db_status calls to include error messages"""
import re

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern: except Exception as e: ... update_db_status("error")
# Replace with: update_db_status("error", str(e))

patterns = [
    # Step 1 - general exception
    (r'(except Exception as e:.*?Step 1 failed.*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2error_msg = str(e)\n\2update_db_status("error", f"Step 1: {error_msg}")'),
    
    # Step 1 - HTML not found
    (r'(HTML file not found after.*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", "Step 1: HTML file not found after timeout")'),
    
    # Step 2 - JSON not found
    (r'(error_msg = f"JSON file not found: .*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", error_msg)'),
    
    # Step 2 - No listings
    (r'(error_msg = f"No listings found in JSON".*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", error_msg)'),
    
    # Step 2 - general exception
    (r'(except Exception as e:.*?Step 2 failed.*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", f"Step 2: {str(e)}")'),
    
    # Step 3 - general exception
    (r'(except Exception as e:.*?Step 3 failed.*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", f"Step 3: {str(e)}")'),
    
    # Step 4 - general exception
    (r'(except Exception as e:.*?Step 4 failed.*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", f"Step 4: {str(e)}")'),
    
    # Step 5 - general exceptions
    (r'(except Exception as e:.*?Step 5 failed.*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", f"Step 5: {str(e)}")'),
    
    # Step 6 - general exception
    (r'(except Exception as e:.*?Step 6 failed.*?)\n(\s+)update_db_status\("error"\)',
     r'\1\n\2update_db_status("error", f"Step 6: {str(e)}")'),
]

changes = 0
for pattern, replacement in patterns:
    new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if count > 0:
        content = new_content
        changes += count
        print(f"✓ Applied pattern (matched {count} time(s))")

if changes > 0:
    with open('config_hud.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n✅ Updated {changes} error handlers to include error messages")
else:
    print("⚠️ No patterns matched - might need manual updates")
