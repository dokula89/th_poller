#!/usr/bin/env python3
"""Fix the massive indentation issue by wrapping lines 4207-4362 in a try block"""

file_path = r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines 4207-4362 (0-indexed: 4206-4361) need to be indented by 4 spaces
# because they're now inside a try block
for i in range(4210, min(4362, len(lines))):  # Starting from line 4211 (after the new 'try:' at 4207)
    lines[i] = '    ' + lines[i]

# Now remove the duplicate try block and its comment at lines 4365-4366
# After our indentation, these will be at different line numbers
# Let's find them by content
for i in range(4360, min(4370, len(lines))):
    if '# ...existing code...' in lines[i]:
        # Remove this line and the try: before it
        if i > 0 and 'try:' in lines[i-1]:
            lines[i-1] = ''  # Remove try:
        lines[i] = ''  # Remove comment

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Indented lines 4211-4361 by 4 spaces")
print("✓ Removed duplicate try block")
