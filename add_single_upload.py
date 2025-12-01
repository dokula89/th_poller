"""
Add upload call for single parcel mode
"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with "Only reset buttons if not in batch mode"
for i, line in enumerate(lines):
    if '# Only reset buttons if not in batch mode' in line and i > 600:
        # Found it! Now insert the upload call before resetting buttons
        # The structure is:
        # Line i: # Only reset buttons if not in batch mode
        # Line i+1: if not hasattr(self, '_in_batch_mode') or not self._in_batch_mode:
        # Line i+2: self.window.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
        
        # Insert upload call after the if statement, before button resets
        indent = '                '  # 16 spaces (inside if block)
        upload_lines = [
            indent + '# For single parcel mode, upload to database immediately\n',
            indent + 'self.window.after(0, lambda: self.append_log("=== Single parcel extraction complete ==="))\n',
            indent + 'self.window.after(0, lambda: self.append_log("Starting database upload..."))\n',
            indent + 'self.upload_all_to_database()\n',
            indent + '\n',
        ]
        
        # Insert after the if line (at i+2, before first window.after)
        for idx, upload_line in enumerate(upload_lines):
            lines.insert(i + 2 + idx, upload_line)
        
        print(f"✓ Added upload call at line {i+3}")
        break

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Single parcel mode will now upload to database after extraction!")
