#!/usr/bin/env python3
"""Completely rewrite the success block"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the "else:" for successful upload (around line 1366)
for i in range(1360, 1380):
    if i < len(lines) and lines[i].strip() == 'else:':
        # Check if this is the upload success else block
        if i > 1360 and 'uploaded_count <' in lines[i-2]:
            print(f"Found success else block at line {i+1}")
            
            # Find the end of this else block (look for next unindented line or next major section)
            end_idx = i + 1
            while end_idx < len(lines):
                # Look for "# Refresh the parcel table" comment
                if '# Refresh the parcel table' in lines[end_idx]:
                    break
                end_idx += 1
            
            print(f"Block ends at line {end_idx}")
            
            # Replace the entire else block with clean code
            new_else_block = [
                "            else:\n",
                "                self.window.after(0, lambda u=uploaded_count, t=total_records: self.append_log(f\"✓ Upload complete! {u}/{t} records saved\"))\n",
                "                self.window.after(0, lambda u=uploaded_count, t=total_records: self.update_status(f\"✓ Upload complete! {u}/{t} records saved\", 9))\n",
                "                self.window.after(0, lambda u=uploaded_count, t=total_records: self.batch_progress_label.config(text=f\"Database upload complete: {u}/{t}\"))\n",
                "                # Clear JSON file after successful upload\n",
                "                self.window.after(0, lambda: self.append_log(\"Clearing parcels_data.json...\"))\n",
                "                with open(json_path, 'w', encoding='utf-8') as f:\n",
                "                    json.dump([], f)\n",
                "\n",
            ]
            
            # Replace
            lines = lines[:i] + new_else_block + lines[end_idx:]
            print(f"✓ Replaced lines {i+1} to {end_idx} with clean success block")
            break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Fixed the success block with proper indentation!")
