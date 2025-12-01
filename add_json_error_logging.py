#!/usr/bin/env python3
"""Add exception logging to activity log for JSON save"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the exception handler for JSON save
for i, line in enumerate(lines):
    if 'except Exception as e:' in line and i > 600 and i < 700:
        # Check if next line has "Failed to save JSON"
        if i+1 < len(lines) and 'Failed to save JSON' in lines[i+1]:
            # Add activity log error after the logging.error
            new_lines = [
                "                self.window.after(0, lambda err=str(e): self.append_log(f'✗ JSON SAVE ERROR: {err}'))\n",
                "                import traceback\n",
                "                tb = traceback.format_exc()\n",
                "                self.window.after(0, lambda t=tb: self.append_log(f'Traceback: {t}'))\n",
            ]
            # Insert after the logging.error line
            lines = lines[:i+2] + new_lines + lines[i+2:]
            print(f"✓ Added exception logging to activity log at line {i+2}")
            break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Added JSON save exception logging to activity log")
print("If there's an error, you'll now see it in the activity log!")
