#!/usr/bin/env python3
"""Fix OCR extraction patterns - line by line approach"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: Add "Agora" pattern after line 1070
# Line 1070 (index 1069): r'[Aa]derass[:\s]*([^\n]+)',  # OCR often reads 'dd' as 'der'
if 1069 < len(lines) and "derass" in lines[1069]:
    # Insert new line after 1070
    new_line = "                r'[Aa]gora[:\\s]*([^\\n]+)',  # OCR typo: Address -> Agora\n"
    lines.insert(1070, new_line)
    print("✓ Added 'Agora' pattern at line 1071")
else:
    print("✗ Could not find derass line to insert after")

# Fix 2: Add "Propary" pattern (find property_name section)
for i, line in enumerate(lines):
    if "'property_name': [" in line:
        # Find the line with the generic "name" pattern
        for j in range(i+1, min(i+10, len(lines))):
            if "r'name[:" in lines[j] and "Flexible" in lines[j]:
                # Insert before this line
                new_line = "                r'[Pp]ropary\\s*name[:\\s]*([^\\n]+)',  # OCR typo: Property -> Propary\n"
                lines.insert(j, new_line)
                print(f"✓ Added 'Propary' pattern at line {j+1}")
                break
        break

# Fix 3: Add "Juracicion" pattern (find jurisdiction section)
for i, line in enumerate(lines):
    if "'jurisdiction': [" in line:
        # Find the line with SEATTLE pattern
        for j in range(i+1, min(i+10, len(lines))):
            if "SEATTLE" in lines[j] and "Common jurisdictions" in lines[j]:
                # Insert before this line
                new_line = "                r'[Jj]uracicion[:\\s]*([^\\n]+)',  # OCR typo: Jurisdiction -> Juracicion\n"
                lines.insert(j, new_line)
                print(f"✓ Added 'Juracicion' pattern at line {j+1}")
                break
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ All OCR typo patterns added!")
print("\nAdded patterns:")
print("  - 'Agora' for Address")
print("  - 'Propary' for Property")
print("  - 'Juracicion' for Jurisdiction")
print("\nClose and restart the automation window!")
