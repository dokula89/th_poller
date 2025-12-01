#!/usr/bin/env python3
"""Add logging to track JSON append"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find line with all_data.append(extracted_data)
for i, line in enumerate(lines):
    if 'all_data.append(extracted_data)' in line.strip():
        # Check if logging not already added (look for our specific message)
        if i > 0 and 'Saving to JSON' not in lines[i-1]:
            # Add logging before
            indent = "                "  # Match the indentation
            new_lines_before = [
                f"{indent}self.window.after(0, lambda p=json_path: self.append_log(f'Saving to JSON: {{p}}'))\n",
                f"{indent}self.window.after(0, lambda c=len(all_data): self.append_log(f'Current records in file: {{c}}'))\n",
            ]
            new_lines_after = [
                f"{indent}self.window.after(0, lambda c=len(all_data): self.append_log(f'After append: {{c}} records'))\n",
            ]
            lines = lines[:i] + new_lines_before + [lines[i]] + new_lines_after + lines[i+1:]
            print(f"✓ Added JSON append logging around line {i+1}")
            break
else:
    print("✗ Could not find all_data.append line")

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Done!")
