#!/usr/bin/env python3
"""Add OCR text logging to activity log"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line after logging.info("=== End OCR Text ===")
target_line = None
for i, line in enumerate(lines):
    if '=== End OCR Text ===' in line and 'logging.info' in line:
        target_line = i + 1
        break

if target_line is None:
    print("ERROR: Could not find target line")
    exit(1)

print(f"Found target at line {target_line + 1}")

# Insert new lines after the logging.info line
new_code = [
    "        \n",
    "        # Also show in activity log for real-time debugging\n",
    "        self.window.after(0, lambda: self.append_log(f\"=== RAW OCR TEXT ({len(ocr_text)} chars) ===\"))\n",
    "        # Show first 800 chars to see field structure\n",
    "        preview_text = ocr_text[:800] if len(ocr_text) > 800 else ocr_text\n",
    "        self.window.after(0, lambda t=preview_text: self.append_log(t))\n",
    "        self.window.after(0, lambda: self.append_log(\"=== END RAW OCR ===\"))\n",
]

# Insert the new lines
lines = lines[:target_line] + new_code + lines[target_line:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✓ Added {len(new_code)} lines of OCR activity logging")
print("Run the automation again and check the activity log to see raw OCR text!")
