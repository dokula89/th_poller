#!/usr/bin/env python3
"""Add specific logging for num_units extraction attempts"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where we try to extract num_units and add detailed logging
for i, line in enumerate(lines):
    if 'for field, pattern_list in patterns.items():' in line:
        # Find the section inside the loop where we try each pattern
        for j in range(i, i+15):
            if 'for pattern in pattern_list:' in lines[j]:
                # Add logging right after this line
                indent = '                '
                new_lines = [
                    f"{indent}if field == 'num_units':  # Debug num_units specifically\n",
                    f"{indent}    logging.info(f'Trying num_units pattern: {{pattern}}')\n",
                ]
                # Insert after the for pattern line
                lines = lines[:j+1] + new_lines + lines[j+1:]
                print(f"✓ Added num_units debug logging at line {j+2}")
                break
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Added detailed logging for num_units extraction")
print("This will show each pattern being tried for # of units")
