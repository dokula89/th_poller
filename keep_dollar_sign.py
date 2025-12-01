#!/usr/bin/env python3
"""Remove $ stripping from address patterns"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix address patterns - remove \$? to keep $ in the value
for i, line in enumerate(lines):
    if "'address': [" in line:
        # Update the next 3 pattern lines
        for j in range(i+1, i+5):
            if j < len(lines) and r'\$?([0-9][^\n]+)' in lines[j]:
                # Remove \$? and change to just capture everything
                lines[j] = lines[j].replace(r'\$?([0-9][^\n]+)', r'([^\n]+)')
                print(f"✓ Updated address pattern at line {j+1}")

# Also check appraised_value - keep $ there too
for i, line in enumerate(lines):
    if "'appraised_value': [" in line:
        # Update the next 2 pattern lines
        for j in range(i+1, i+4):
            if j < len(lines) and r'\$?' in lines[j] and r'[\d,]+' in lines[j]:
                # Change to capture $ along with the digits
                lines[j] = lines[j].replace(r'\$?([\d,]+)', r'(\$?[\d,]+)')
                print(f"✓ Updated appraised_value pattern at line {j+1}")

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Removed $ stripping - values will include $ symbol!")
