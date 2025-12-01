#!/usr/bin/env python3
"""Adjust column widths and fix missing levy_code and num_units patterns"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: Adjust column widths
for i, line in enumerate(lines):
    if 'self.json_tree.column("field"' in line:
        lines[i] = '        self.json_tree.column("field", width=150, minwidth=120)\n'
        print(f"✓ Updated field column width at line {i+1}")
    elif 'self.json_tree.column("value"' in line:
        lines[i] = '        self.json_tree.column("value", width=600, minwidth=400)\n'
        print(f"✓ Updated value column width at line {i+1}")

# Fix 2: Update levy_code and num_units patterns - they might have blank lines
# Find the patterns section
for i, line in enumerate(lines):
    if "'levy_code': [" in line:
        # Replace the levy_code patterns to handle possible whitespace/blank lines
        for j in range(i+1, i+5):
            if 'Lavy' in lines[j] or 'Levy' in lines[j] or 'levy' in lines[j]:
                # Update to be more flexible with whitespace
                if 'Lavy' in lines[j]:
                    lines[j] = "                r'[Ll]avy\\s*cade[:\\s]*([\\d]+)',  # OCR: Lavy cade\n"
                    print(f"✓ Updated Lavy cade pattern at line {j+1}")
                elif 'evy' in lines[j] and 'code' in lines[j]:
                    lines[j] = "                r'[Ll]evy\\s*code[:\\s]*([\\d]+)',\n"
                    print(f"✓ Updated Levy code pattern at line {j+1}")

for i, line in enumerate(lines):
    if "'num_units': [" in line:
        # Replace num_units patterns
        for j in range(i+1, i+5):
            if 'unks' in lines[j] or 'units' in lines[j]:
                if 'unks' in lines[j]:
                    lines[j] = "                r'#\\s*at\\s*unks[:\\s]*([\\d]+)',  # OCR: # at unks\n"
                    print(f"✓ Updated # at unks pattern at line {j+1}")
                elif 'of\\s*units' in lines[j]:
                    lines[j] = "                r'#\\s*of\\s*units[:\\s]*([\\d]+)',\n"
                    print(f"✓ Updated # of units pattern at line {j+1}")

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Updated column widths (Field: 150px, Value: 600px)")
print("✓ Updated levy_code and num_units patterns")
