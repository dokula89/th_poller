#!/usr/bin/env python3
"""Only clear JSON file AFTER successful upload"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the section that clears the JSON file
clear_start = None
clear_end = None

for i, line in enumerate(lines):
    if 'Clearing parcels_data.json' in line:
        clear_start = i
        # Find the json.dump([], f) line
        for j in range(i, i+5):
            if 'json.dump([], f)' in lines[j]:
                clear_end = j
                break
        break

if clear_start is None or clear_end is None:
    print("ERROR: Could not find clearing section")
    exit(1)

print(f"Found clearing section from line {clear_start+1} to {clear_end+1}")

# Find where uploaded_count is checked
success_check = None
for i in range(clear_end, clear_end + 20):
    if 'if uploaded_count == 0:' in lines[i]:
        success_check = i
        break

if success_check is None:
    print("ERROR: Could not find success check")
    exit(1)

print(f"Found success check at line {success_check+1}")

# Move the clearing code to AFTER the success check, inside the "else" (success) block
# First, extract the clearing lines
clearing_lines = lines[clear_start:clear_end+1]

# Remove the clearing lines from their current position
lines = lines[:clear_start] + lines[clear_end+1:]

# Adjust the success_check index (it shifted up)
success_check = success_check - (clear_end - clear_start + 1)

# Find the final "else:" block (successful upload)
for i in range(success_check, success_check + 15):
    if lines[i].strip() == 'else:':
        # Insert clearing code after this else: block's first line
        # Find the next line after else:
        insert_pos = i + 1
        # Skip any existing lines in the else block to find where to insert
        while insert_pos < len(lines) and (lines[insert_pos].strip().startswith('self.window.after') or lines[insert_pos].strip().startswith('self.update_status')):
            insert_pos += 1
        
        # Insert clearing code here
        lines = lines[:insert_pos] + clearing_lines + lines[insert_pos:]
        print(f"✓ Moved clearing code to line {insert_pos+1} (inside success block)")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ JSON file will now only be cleared AFTER successful upload!")
print("If upload fails, the data will remain in the JSON file.")
