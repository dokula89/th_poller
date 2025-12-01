#!/usr/bin/env python3
"""Add pattern to capture whatever comes after # at unks: even if not digits"""

# Read the file  
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find num_units patterns
for i, line in enumerate(lines):
    if "'num_units': [" in line:
        new_patterns = [
            "            'num_units': [\n",
            "                r'(\\d+)\\s*\\n+\\s*#\\s*at\\s*unks:',  # Number BEFORE label\n",
            "                r'(\\d+)\\s*\\n+\\s*#\\s*of\\s*units:',  # Number BEFORE label\n",
            "                r'#\\s*at\\s*unks[:\\s]+(\\d+)',  # Digits after label\n",
            "                r'#\\s*of\\s*units[:\\s]+(\\d+)',  # Digits after label\n",
            "                r'#\\s*at\\s*unks[:\\s]*\\n+\\s*([^\\n]+?(?=\\s*\\n))',  # ANY text after label (including =))\n",
            "            ],\n",
        ]
        
        # Find end
        end_idx = i + 1
        while end_idx < len(lines) and '],\n' not in lines[end_idx]:
            end_idx += 1
        end_idx += 1
        
        # Replace
        lines = lines[:i] + new_patterns + lines[end_idx:]
        print(f"✓ Updated num_units to capture any text after label")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ num_units will now capture '=)' or any other OCR text")
print("You can manually check and correct if needed")
