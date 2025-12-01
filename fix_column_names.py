"""
Fix column names in INSERT query to match actual database schema
"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the INSERT SQL to match actual column names
old_insert = '''                    insert_sql = """
                        INSERT INTO king_county_parcels
                        (google_addresses_id, parcel_number, property_name, jurisdiction, taxpayer_name,
                         address, appraised_value, lot_area, levy_code, num_units, num_buildings,
                         raw_ocr_text, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """'''

new_insert = '''                    insert_sql = """
                        INSERT INTO king_county_parcels
                        (google_addresses_id, parcel_number, Property_name, Jurisdiction, Taxpayer_name,
                         Address, Appraised_value, Lot_area, Levy_code, num_of_units, num_of_buildings,
                         time_inserted)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UNIX_TIMESTAMP())
                    """'''

content = content.replace(old_insert, new_insert)

# Also need to remove raw_ocr_text from values since it's not in the table
old_values = '''                    values = (
                        google_address_id,
                        fields.get('parcel_number'),
                        fields.get('property_name'),
                        fields.get('jurisdiction'),
                        fields.get('taxpayer_name'),
                        fields.get('address'),
                        fields.get('appraised_value'),
                        fields.get('lot_area'),
                        fields.get('levy_code'),
                        fields.get('num_units'),
                        fields.get('num_buildings'),
                        extracted_data.get('raw_text', '')[:5000],
                    )'''

new_values = '''                    values = (
                        google_address_id,
                        fields.get('parcel_number'),
                        fields.get('property_name'),
                        fields.get('jurisdiction'),
                        fields.get('taxpayer_name'),
                        fields.get('address'),
                        fields.get('appraised_value'),
                        fields.get('lot_area'),
                        fields.get('levy_code'),
                        fields.get('num_units'),
                        fields.get('num_buildings'),
                    )'''

content = content.replace(old_values, new_values)

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Fixed column names to match database schema:")
print("  - property_name → Property_name")
print("  - jurisdiction → Jurisdiction")
print("  - taxpayer_name → Taxpayer_name")
print("  - address → Address")
print("  - appraised_value → Appraised_value")
print("  - lot_area → Lot_area")
print("  - levy_code → Levy_code")
print("  - num_units → num_of_units")
print("  - num_buildings → num_of_buildings")
print("  - Removed raw_ocr_text (not in table)")
print("  - created_at → time_inserted with UNIX_TIMESTAMP()")
