#!/usr/bin/env python3
"""Fix lines 1367-1375 directly"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Replace lines 1367-1375 (indices 1366-1374)
new_lines = [
    "            else:\n",
    "                self.window.after(0, lambda u=uploaded_count, t=total_records: self.append_log(f\"✓ Upload complete! {u}/{t} records saved\"))\n",
    "                self.window.after(0, lambda u=uploaded_count, t=total_records: self.update_status(f\"✓ Upload complete! {u}/{t} records saved\", 9))\n",
    "                self.window.after(0, lambda u=uploaded_count, t=total_records: self.batch_progress_label.config(text=f\"Database upload complete: {u}/{t}\"))\n",
    "                # Clear JSON file after successful upload\n",
    "                self.window.after(0, lambda: self.append_log(\"Clearing parcels_data.json...\"))\n",
    "                with open(json_path, 'w', encoding='utf-8') as f:\n",
    "                    json.dump([], f)\n",
]

# Replace lines 1366-1374 (indices 1366-1374, 9 lines)
lines = lines[:1366] + new_lines + lines[1375:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Fixed lines 1367-1375 with clean code!")
