#!/usr/bin/env python3
"""Add more flexible num_units patterns to handle OCR garbage and look between labels"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find num_units patterns
for i, line in enumerate(lines):
    if "'num_units': [" in line:
        # Add more patterns including looking for numbers between lot_area and levy_code labels
        new_patterns = [
            "            'num_units': [\n",
            "                # Look for number between lot_area and levy_code sections\n",
            "                r'[Ll]ot\\s*aren[:\\s]*\\n+\\s*([\\d,\\.]+)\\s*\\n+\\s*([\\d]+)\\s*\\n+\\s*[Ll]avy\\s*cade:',  # Captures 2nd number\n",
            "                r'(\\d+)\\s*\\n+\\s*#\\s*at\\s*unks:',  # Number BEFORE label\n",
            "                r'(\\d+)\\s*\\n+\\s*#\\s*of\\s*units:',  # Number BEFORE label\n",
            "                r'#\\s*at\\s*unks[:\\s]+([\\d]+)',  # After label\n",
            "                r'#\\s*of\\s*units[:\\s]+([\\d]+)',  # After label\n",
            "                r'#\\s*at\\s*unks[:\\s]*\\n+\\s*([^\\n]+)',  # Anything after label (including OCR garbage)\n",
            "            ],\n",
        ]
        
        # Find end of current num_units block
        end_idx = i + 1
        while end_idx < len(lines) and '],\n' not in lines[end_idx]:
            end_idx += 1
        end_idx += 1
        
        # Replace
        lines = lines[:i] + new_patterns + lines[end_idx:]
        print(f"✓ Updated num_units patterns with more flexible matching")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Added flexible num_units patterns!")
print("Will now capture:")
print("  - Numbers appearing between lot_area and levy_code")
print("  - Numbers before # at unks: label")  
print("  - Any text after # at unks: (will need manual validation)")
