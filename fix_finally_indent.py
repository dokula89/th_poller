#!/usr/bin/env python3
"""Fix the indentation of the finally block in config_utils.py"""

file_path = r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines 4388-4838 need to be properly indented inside the finally block
# The finally: is at line 4387 (index 4386)
# Everything from line 4388 (index 4387) to 4838 should be inside finally

# First, let's remove the extra indentation we just added
for i in range(4387, min(4838, len(lines))):
    if lines[i].startswith('    ') and lines[i][4:8] != '    ':
        # Remove the 4 spaces we just added
        lines[i] = lines[i][4:]

# Now properly indent based on structure
# The finally block should have everything at base_indent + 4
base_indent = 16  # The finally: statement has 16 spaces
finally_content_indent = base_indent + 4  # = 20 spaces

# We need to re-indent from scratch
# Let me read lines 4391-4395 to understand current state
print(f"Line 4391: {repr(lines[4390])}")
print(f"Line 4392: {repr(lines[4391])}")
print(f"Line 4393: {repr(lines[4392])}")
print(f"Line 4394: {repr(lines[4393])}")
print(f"Line 4395: {repr(lines[4394])}")
