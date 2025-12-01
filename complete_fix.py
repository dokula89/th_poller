"""
Complete fix - reconstruct the whole upload function properly
"""
import re

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the function and replace it entirely
# First, extract everything before the function
pattern = r'(.*?)(    def upload_all_to_database\(self\):.*?)(    def refresh_parent_table\(self\):)'
match = re.search(pattern, content, re.DOTALL)

if match:
    before = match.group(1)
    after_func_start = match.group(3)  # This is the next function
    
    # Create the complete new function
    new_function = '''    def upload_all_to_database(self):
        """Upload all parcels from JSON to database with progress bar"""
        self.window.after(0, lambda: self.append_log("=== STARTING DATABASE UPLOAD ==="))
        import mysql.connector
        import json

        json_path = self.capture_dir / "parcels_data.json"
        self.window.after(0, lambda p=str(json_path): self.append_log(f"Checking JSON file: {p}"))
        
        if not json_path.exists():
            self.window.after(0, lambda: self.append_log("✗ JSON file not found!"))
            self.window.after(0, lambda: self.update_status("No data to upload"))
            return

        try:
            # Load all data from JSON
            self.window.after(0, lambda: self.append_log("Loading parcels_data.json..."))
            with open(json_path, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
            
            data_count = len(all_data) if isinstance(all_data, list) else 0
            self.window.after(0, lambda d=data_count: self.append_log(f"Loaded {d} records from JSON"))

            if not all_data:
                self.window.after(0, lambda: self.update_status("No records to upload"))
                self.window.after(0, lambda: self.append_log("No records found in JSON"))
                return

            total_records = len(all_data)
            self.window.after(0, lambda t=total_records: self.append_log(f"Found {t} records to upload"))
            self.window.after(0, lambda: self.update_status(f"Uploading {total_records} records to database..."))
            self.window.after(0, lambda: self.update_status("Uploading to database", 8))
            
            # Get database config
            self.window.after(0, lambda: self.append_log("Reading database config..."))
            config_path = Path(__file__).parent / 'config_hud_db.py'
            config_globals = {}
            with open(config_path) as f:
                exec(f.read(), config_globals)
            DB_CONFIG = config_globals.get('DB_CONFIG')
            
            host = DB_CONFIG.get('host', 'unknown')
            self.window.after(0, lambda h=host: self.append_log(f"Connecting to database: {h}"))

            # Connect to database
            self.window.after(0, lambda: self.append_log("Establishing connection..."))
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            self.window.after(0, lambda: self.append_log("✓ Connected to database"))

            uploaded_count = 0

            for idx, extracted_data in enumerate(all_data):
                try:
                    # Update progress
                    progress = int((idx + 1) / total_records * 100)
                    address = extracted_data.get('address', 'Unknown')
                    self.window.after(0, lambda a=address, i=idx, t=total_records: self.append_log(f"Uploading {i+1}/{t}: {a}"))
                    self.window.after(0, lambda p=progress, i=idx, t=total_records: self.batch_progress_label.config(
                        text=f"Uploading to database: {i+1}/{t} ({p}%)"
                    ))
                    self.window.after(0, lambda i=idx: self.batch_progress_var.set(i + 1))
                    
                    # Insert record
                    fields = extracted_data.get('extracted_fields', {})
                    google_address_id = extracted_data.get('id')

                    insert_sql = """
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

                    cursor.execute(insert_sql, values)
                    king_county_parcel_id = cursor.lastrowid

                    logging.info(f"Inserted parcel ID {king_county_parcel_id} for google_address {google_address_id}")
                    
                    # Update google_addresses with king_county_parcels_id
                    if google_address_id:
                        update_sql = """
                            UPDATE google_addresses
                            SET king_county_parcels_id = %s,
                                updated_at = NOW()
                            WHERE id = %s
                        """
                        cursor.execute(update_sql, (king_county_parcel_id, google_address_id))
                        logging.info(f"Updated google_addresses id={google_address_id} with king_county_parcels_id={king_county_parcel_id}")
                    
                    conn.commit()
                    uploaded_count += 1
                    self.window.after(0, lambda: self.append_log("  ✓ Saved to database"))
                    
                except Exception as e:
                    error_msg = str(e)[:100]
                    logging.error(f"Failed to upload record {idx}: {e}")
                    self.window.after(0, lambda err=error_msg: self.append_log(f"  ✗ Error: {err}"))
                    conn.rollback()
                    continue

            cursor.close()
            conn.close()
            self.window.after(0, lambda: self.append_log("✓ Database connection closed"))
            
            # Clear the JSON file after successful upload
            self.window.after(0, lambda: self.append_log("Clearing parcels_data.json..."))
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump([], f)

            logging.info(f"✓ Uploaded {uploaded_count}/{total_records} records to database")
            self.window.after(0, lambda u=uploaded_count, t=total_records: self.append_log(f"✓ Upload complete! {u}/{t} records saved"))
            self.window.after(0, lambda u=uploaded_count, t=total_records: self.update_status(f"✓ Upload complete! {u}/{t} records saved", 9))
            self.window.after(0, lambda u=uploaded_count, t=total_records: self.batch_progress_label.config(
                text=f"Database upload complete: {u}/{t}"
            ))

            # Refresh the parcel table in the main UI
            self.window.after(0, lambda: self.append_log("Refreshing parent table..."))
            self.refresh_parent_table()
            self.window.after(0, lambda: self.append_log("✓ All done!"))

        except Exception as e:
            import traceback
            full_error = traceback.format_exc()
            logging.error(f"DATABASE UPLOAD FAILED: {e}")
            logging.error(f"Full traceback:\\n{full_error}")
            
            # Show detailed error in activity log
            self.window.after(0, lambda: self.append_log("=== ✗ UPLOAD FAILED ==="))
            self.window.after(0, lambda err=str(e): self.append_log(f"Error: {err}"))
            self.window.after(0, lambda: self.append_log("Traceback (most recent):"))
            
            # Show last 5 lines of traceback
            tb_lines = [line for line in full_error.split('\\n') if line.strip()]
            for tb_line in tb_lines[-5:]:
                self.window.after(0, lambda l=tb_line: self.append_log(f"  {l}"))
            
            error_msg = str(e)[:200]
            self.window.after(0, lambda err=error_msg: self.update_status(f"Upload error: {err}"))

'''
    
    # Reconstruct the file
    new_content = before + new_function + '\n' + after_func_start
    
    with open('parcel_automation.py', 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print("✓ Successfully replaced upload_all_to_database function!")
else:
    print("✗ Could not find the function to replace")
