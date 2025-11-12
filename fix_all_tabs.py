#!/usr/bin/env python3
"""
Comment out the problematic else block (Networks/Websites/etc tabs)
to get a minimal working UI
"""

filepath = r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py"

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the else block at line 4067 (0-indexed: 4066)
# It ends somewhere around line 4255 where _update_ui is defined
# Let's find it more precisely

start_idx = 4066  # Line 4067: else:
end_idx = None

# Find where this else block ends - look for the next function or major block at same/lower indentation
for i in range(start_idx + 1, len(lines)):
    line = lines[i]
    # Check if we've reached something at 12 spaces or less (outside the else block)
    if line.strip() and not line.startswith(' ' * 13):
        # Found end of else block
        if 'def _update_ui' in line or 'self._refresh_queue_table' in line:
            end_idx = i
            print(f"Found end of else block at line {i+1}: {line[:50].strip()}")
            break

if not end_idx:
    print("Could not find end, using line 4620")
    end_idx = 4619  # Fallback

# Replace the entire else block with a simple disabled message
replacement = '''            else:
                # COMMENTED OUT: Networks/Websites/Accounts/Code tabs - has indentation issues
                error_occurred = True
                error_msg = "This tab is temporarily disabled"
                log_to_file(f"[Queue] Tab {current_table}: {error_msg}")
                rows = []
'''

# Remove old else block and insert new one
new_lines = lines[:start_idx] + [replacement] + lines[end_idx:]

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f'✓ Replaced lines {start_idx+1} to {end_idx} with disabled message')

# Test compilation
import subprocess
import sys
result = subprocess.run([sys.executable, '-m', 'py_compile', filepath], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print('✓ File compiles successfully!')
    print('\nNow try launching the UI!')
else:
    print('✗ Compilation error:')
    print(result.stderr[:500])
