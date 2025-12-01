#!/usr/bin/env python3
"""Make field column smaller and add debug logging for missing fields"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix 1: Make field column smaller (currently 150)
for i, line in enumerate(lines):
    if 'self.json_tree.column("field"' in line and 'width=150' in line:
        lines[i] = '        self.json_tree.column("field", width=120, minwidth=100)\n'
        print(f"✓ Reduced field column width from 150 to 120 at line {i+1}")
        break

# Fix 2: Add logging after pattern matching to see what's being extracted
for i, line in enumerate(lines):
    if 'for field, pattern_list in patterns.items():' in line:
        # Find the section where we check if field was not found
        for j in range(i, i+20):
            if 'if field not in data' in lines[j] and 'extracted_fields' in lines[j]:
                # Add detailed logging
                new_log = "                logging.warning(f\"✗ Could not extract {field} - tried {len(pattern_list)} patterns\")\n"
                # Check if this logging already exists
                if j+1 < len(lines) and 'Could not extract' not in lines[j+1]:
                    lines.insert(j+1, new_log)
                    print(f"✓ Added missing field logging at line {j+2}")
                break
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Field column width reduced to 120px")
print("✓ Added logging for missing fields")
print("\nClose and restart, then check activity log for extraction details")
