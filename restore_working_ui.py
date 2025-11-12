#!/usr/bin/env python3
"""
Restore config_utils.py to the last working state where UI opened successfully.
This applies all the indentation fixes that were done in the session.
"""

filepath = r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py"

print("Reading file...")
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")

# Fix 1: Lines 4210-4367 (Networks API fetch) - indent by 8 spaces (4 for if, 4 for try)
print("Fix 1: Indenting lines 4210-4367...")
for i in range(4209, 4367):  # 0-indexed
    lines[i] = '        ' + lines[i]

# Fix 2: Lines 4371-4390 (exception handlers) - indent to 16 spaces
print("Fix 2: Indenting exception handlers...")
for i in range(4370, 4390):
    if lines[i].strip().startswith(('except', 'finally', 'log_to_file', 'log_exception', 'error_occurred', 'error_msg')):
        lines[i] = '                ' + lines[i].lstrip()

# Fix 3: Lines 4381-4755 (finally block content) - indent by 4 spaces  
print("Fix 3: Indenting finally block...")
for i in range(4380, 4755):
    if not lines[i].strip().startswith(('except', 'finally')) and lines[i].strip():
        lines[i] = '    ' + lines[i]

# Fix 4: Line 4753-4754 (UI update call) - adjust to 20 spaces
print("Fix 4: Adjusting UI update call indentation...")
for i in range(4752, 4754):
    if 'self._root.after' in lines[i]:
        lines[i] = '                    ' + lines[i].lstrip()

# Fix 5: Lines 4828-4829 (count fetch finally) - adjust to 16 spaces
print("Fix 5: Adjusting count fetch finally...")
for i in range(4827, 4829):
    if lines[i].strip():
        lines[i] = '                ' + lines[i].lstrip()

# Fix 6: Lines 5028-5030 (Accounts UI update) - adjust to 36 spaces
print("Fix 6: Adjusting accounts UI update...")
for i in range(5027, 5030):
    if lines[i].strip():
        lines[i] = '                                    ' + lines[i].lstrip()

# Fix 7: Lines 5031-5037 (exception handler) - adjust to 24 spaces
print("Fix 7: Adjusting exception handler...")
for i in range(5030, 5037):
    if lines[i].strip():
        lines[i] = '                        ' + lines[i].lstrip()

# Fix 8: Lines 5079-5091 (show accounts exception) - adjust to 8 spaces
print("Fix 8: Adjusting show accounts exception...")
for i in range(5078, 5091):
    if lines[i].strip():
        lines[i] = '        ' + lines[i].lstrip()

print("Writing fixed file...")
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ All indentation fixes applied!")
print("\nNow compiling to check for errors...")

import subprocess
import sys
result = subprocess.run([sys.executable, '-m', 'py_compile', filepath], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print("✓ File compiles successfully!")
else:
    print("✗ Compilation errors:")
    print(result.stderr)
