#!/usr/bin/env python3
"""Fix extraction issues based on OCR output"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: Add "Lot aren" pattern (OCR reads "Lot area" as "Lot aren")
for i, line in enumerate(lines):
    if "'lot_area': [" in line:
        # Find the line with the last pattern before closing bracket
        for j in range(i+1, min(i+10, len(lines))):
            if "],\n" == lines[j] or "]," in lines[j]:
                # Insert before the closing bracket
                new_line = "                r'[Ll]ot\\s*aren[:\\s]*([\\d,\\.]+)',  # OCR typo: area -> aren\n"
                lines.insert(j, new_line)
                print(f"✓ Added 'Lot aren' pattern at line {j+1}")
                break
        break

# Fix 2: Add pattern to handle $ before address numbers
for i, line in enumerate(lines):
    if "'address': [" in line:
        # Find where to add - after the Agora pattern
        for j in range(i+1, min(i+10, len(lines))):
            if "Agora" in lines[j]:
                # Modify this line to strip $ character
                # Actually, let's add a new pattern that handles $ prefix
                new_line = "                r'[Aa]gora[:\\s]*\\$?(.+)',  # OCR typo with optional $\n"
                lines[j] = new_line
                print(f"✓ Updated Agora pattern to strip $ at line {j+1}")
                break
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Fixed extraction patterns!")
print("  - Added 'Lot aren' pattern for lot_area")
print("  - Updated address pattern to strip $ character")
print("\nClose and restart window!")
