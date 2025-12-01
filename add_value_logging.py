"""
Add logging to show actual values being inserted
"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Add logging before INSERT execution to show what values are being used
old_execute = '''                    self.window.after(0, lambda: self.append_log(f"  Executing INSERT for google_address_id={google_address_id}"))
                    cursor.execute(insert_sql, values)'''

new_execute = '''                    self.window.after(0, lambda: self.append_log(f"  Executing INSERT for google_address_id={google_address_id}"))
                    self.window.after(0, lambda v=values: self.append_log(f"  Values: parcel={v[1]}, property={v[2]}, address={v[5]}"))
                    cursor.execute(insert_sql, values)'''

content = content.replace(old_execute, new_execute)

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Added logging to show INSERT values")
print("  Will display: parcel_number, property_name, and address fields")
