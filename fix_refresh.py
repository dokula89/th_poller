"""Add body to refresh_parent_table"""

# Read file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find refresh_parent_table and add body
for i, line in enumerate(lines):
    if 'def refresh_parent_table(self):' in line:
        # Check if next line is empty or another def
        if i+1 < len(lines) and (not lines[i+1].strip() or 'def ' in lines[i+1]):
            # Add the function body
            body = '''        """Refresh the parcel table in the parent window"""
        try:
            # The parent window should have a method to refresh the table
            # This will trigger a reload of data from the database
            if hasattr(self.parent, 'refresh_queue'):
                self.window.after(0, lambda: self.parent.refresh_queue())
                logging.info("✓ Refreshed parent table")
        except Exception as e:
            logging.warning(f"Could not refresh parent table: {e}")

'''
            lines.insert(i+1, body)
            print(f"Added body to refresh_parent_table at line {i+2}")
            break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Fixed refresh_parent_table!")
