#!/usr/bin/env python3
"""Add logging to track JSON save process"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line 619: extracted_data = self.extract_structured_data(extracted_text)
# Add logging right after it
for i, line in enumerate(lines):
    if 'extracted_data = self.extract_structured_data(extracted_text)' in line:
        # Insert logging after this line
        new_lines = [
            "            self.window.after(0, lambda: self.append_log(f\"Data extracted, fields count: {len(extracted_data.get('extracted_fields', {}))}\"))\n",
            "            self.window.after(0, lambda d=extracted_data: self.append_log(f\"Extracted fields: {list(d.get('extracted_fields', {}).keys())}\"))\n",
        ]
        lines = lines[:i+1] + new_lines + lines[i+1:]
        print(f"✓ Added extraction logging after line {i+1}")
        break

# Find the line: all_data.append(extracted_data)
for i, line in enumerate(lines):
    if 'all_data.append(extracted_data)' in line and 'Append new data' in lines[i-2]:
        # Add logging before and after
        new_lines_before = [
            "                self.window.after(0, lambda: self.append_log(f\"Saving to JSON: {json_path}\"))\n",
            "                self.window.after(0, lambda c=len(all_data): self.append_log(f\"Current records in file: {c}\"))\n",
        ]
        new_lines_after = [
            "                self.window.after(0, lambda c=len(all_data): self.append_log(f\"After append: {c} records\"))\n",
        ]
        lines = lines[:i] + new_lines_before + [lines[i]] + new_lines_after + lines[i+1:]
        print(f"✓ Added JSON append logging around line {i+1}")
        break

# Find the line with json.dump
for i, line in enumerate(lines):
    if 'json.dump(all_data, f, indent=2' in line:
        # Add logging after
        new_line = "                self.window.after(0, lambda: self.append_log(f\"✓ JSON saved to file\"))\n"
        lines.insert(i+1, new_line)
        print(f"✓ Added JSON dump success logging after line {i+1}")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Added comprehensive JSON save logging!")
print("Close and restart window to see detailed save process.")
