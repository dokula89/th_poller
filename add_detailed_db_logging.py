"""
Add extremely detailed logging to database upload process
"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Pattern 1: Add logging right after function starts
content = content.replace(
    '    def upload_all_to_database(self):\n        """Upload all parcels from JSON to database with progress bar"""\n        self.window.after(0, lambda: self.append_log("=== STARTING DATABASE UPLOAD ==="))',
    '''    def upload_all_to_database(self):
        """Upload all parcels from JSON to database with progress bar"""
        self.window.after(0, lambda: self.append_log("=== STARTING DATABASE UPLOAD ==="))
        self.window.after(0, lambda: self.append_log("Function called: upload_all_to_database()"))
        logging.info("upload_all_to_database() function called")'''
)

# Pattern 2: Add logging after imports
content = content.replace(
    '        self.window.after(0, lambda: self.append_log("Function called: upload_all_to_database()"))\n        logging.info("upload_all_to_database() function called")\n        import mysql.connector\n        import json',
    '''        self.window.after(0, lambda: self.append_log("Function called: upload_all_to_database()"))
        logging.info("upload_all_to_database() function called")
        
        self.window.after(0, lambda: self.append_log("Importing mysql.connector..."))
        import mysql.connector
        import json
        self.window.after(0, lambda: self.append_log("✓ Imports successful"))'''
)

# Pattern 3: Add logging for config reading with more detail
content = content.replace(
    '''            # Get database config
            self.window.after(0, lambda: self.append_log("Reading database config..."))
            config_path = Path(__file__).parent / 'config_hud_db.py'
            config_globals = {}
            with open(config_path) as f:
                exec(f.read(), config_globals)
            DB_CONFIG = config_globals.get('DB_CONFIG')''',
    '''            # Get database config
            self.window.after(0, lambda: self.append_log("Reading database config..."))
            config_path = Path(__file__).parent / 'config_hud_db.py'
            self.window.after(0, lambda p=str(config_path): self.append_log(f"Config path: {p}"))
            
            config_globals = {}
            with open(config_path) as f:
                exec(f.read(), config_globals)
            DB_CONFIG = config_globals.get('DB_CONFIG')
            
            self.window.after(0, lambda: self.append_log(f"Config loaded: host={DB_CONFIG.get('host')}, database={DB_CONFIG.get('database')}, user={DB_CONFIG.get('user')}"))'''
)

# Pattern 4: Add detailed connection logging
content = content.replace(
    '''            host = DB_CONFIG.get('host', 'unknown')
            self.window.after(0, lambda h=host: self.append_log(f"Connecting to database: {h}"))

            # Connect to database
            self.window.after(0, lambda: self.append_log("Establishing connection..."))
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            self.window.after(0, lambda: self.append_log("✓ Connected to database"))''',
    '''            host = DB_CONFIG.get('host', 'unknown')
            database = DB_CONFIG.get('database', 'unknown')
            self.window.after(0, lambda h=host, d=database: self.append_log(f"Target: {h}/{d}"))

            # Connect to database
            self.window.after(0, lambda: self.append_log("Calling mysql.connector.connect()..."))
            try:
                conn = mysql.connector.connect(**DB_CONFIG)
                self.window.after(0, lambda: self.append_log("✓ Connection object created"))
            except Exception as conn_err:
                self.window.after(0, lambda e=str(conn_err): self.append_log(f"✗ Connection failed: {e}"))
                raise
            
            self.window.after(0, lambda: self.append_log("Creating cursor..."))
            cursor = conn.cursor()
            self.window.after(0, lambda: self.append_log("✓ Cursor created, ready to execute queries"))'''
)

# Pattern 5: Add SQL query logging for INSERT
content = content.replace(
    '''                    insert_sql = """
                        INSERT INTO king_county_parcels
                        (google_addresses_id, parcel_number, property_name, jurisdiction, taxpayer_name,
                         address, appraised_value, lot_area, levy_code, num_units, num_buildings,
                         raw_ocr_text, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """

                    values = (
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
                    )

                    cursor.execute(insert_sql, values)''',
    '''                    insert_sql = """
                        INSERT INTO king_county_parcels
                        (google_addresses_id, parcel_number, property_name, jurisdiction, taxpayer_name,
                         address, appraised_value, lot_area, levy_code, num_units, num_buildings,
                         raw_ocr_text, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                    """

                    values = (
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
                    )

                    self.window.after(0, lambda: self.append_log(f"  Executing INSERT for google_address_id={google_address_id}"))
                    cursor.execute(insert_sql, values)
                    self.window.after(0, lambda: self.append_log(f"  ✓ INSERT executed"))'''
)

# Pattern 6: Add logging for UPDATE query
content = content.replace(
    '''                    # Update google_addresses with king_county_parcels_id
                    if google_address_id:
                        update_sql = """
                            UPDATE google_addresses
                            SET king_county_parcels_id = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """
                        cursor.execute(update_sql, (king_county_parcel_id, google_address_id))''',
    '''                    # Update google_addresses with king_county_parcels_id
                    if google_address_id:
                        update_sql = """
                            UPDATE google_addresses
                            SET king_county_parcels_id = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """
                        self.window.after(0, lambda k=king_county_parcel_id, g=google_address_id: self.append_log(f"  Executing UPDATE google_addresses id={g} with parcel_id={k}"))
                        cursor.execute(update_sql, (king_county_parcel_id, google_address_id))
                        self.window.after(0, lambda: self.append_log(f"  ✓ UPDATE executed"))'''
)

# Pattern 7: Add commit logging
content = content.replace(
    '''                    conn.commit()
                    uploaded_count += 1
                    self.window.after(0, lambda: self.append_log("  ✓ Saved to database"))''',
    '''                    self.window.after(0, lambda: self.append_log(f"  Committing transaction..."))
                    conn.commit()
                    uploaded_count += 1
                    self.window.after(0, lambda: self.append_log("  ✓ Transaction committed, saved to database"))'''
)

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Added extremely detailed database logging!")
print("\nThe activity log will now show:")
print("  - Function entry")
print("  - Import status")
print("  - Config file path and contents")
print("  - Database connection details (host/database)")
print("  - Connection and cursor creation")
print("  - Each INSERT query execution")
print("  - Each UPDATE query execution")
print("  - Transaction commits")
print("  - Any connection errors")
