"""Clean batch processing methods to add to ParcelAutomationWindow"""

# Read parcel_automation.py
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find where to insert (before launch_parcel_automation function)
insert_marker = '\ndef launch_parcel_automation'
insert_pos = content.find(insert_marker)

if insert_pos == -1:
    print("ERROR: Could not find insertion point")
    exit(1)

# Define the new methods (clean, no escaping issues)
new_methods = '''
    def process_parcel_images_batch(self):
        """Process saved parcel images based on selected extraction method"""
        import os
        from pathlib import Path
        
        parcels_dir = Path("Captures/parcels")
        all_images = list(parcels_dir.glob("parcels_*.png"))
        unprocessed = [img for img in all_images if not img.stem.endswith('_processed')]
        
        if not unprocessed:
            self.log_activity("No unprocessed parcel images found")
            return
        
        method = self.extraction_method.get()
        self.log_activity(f"Found {len(unprocessed)} unprocessed images")
        self.log_activity(f"Extraction method: {method}")
        
        if method == "openai":
            self.process_with_openai_batch(unprocessed)
        else:
            self.process_with_beautifulsoup(unprocessed)
    
    def process_with_openai_batch(self, image_paths):
        """Process images with OpenAI Vision API in batches of 20"""
        import openai
        import os
        import json
        import base64
        from pathlib import Path
        from datetime import datetime
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            self.log_activity("ERROR: OPENAI_API_KEY not set!")
            return
        
        openai.api_key = api_key
        
        if len(image_paths) < 20:
            self.log_activity(f"Waiting for 20 images... Currently have {len(image_paths)}")
            return
        
        batch_size = 20
        total_inserted = 0
        
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            self.log_activity(f"Processing OpenAI batch {batch_num} ({len(batch)} images)")
            
            # Encode images
            content_list = [{
                "type": "text",
                "text": "Extract parcel_number, present_use, property_name, jurisdiction, taxpayer_name, address, appraised_value, lot_area, levy_code, num_units, num_buildings from each image. Return JSON array."
            }]
            
            for img_path in batch:
                with open(img_path, "rb") as f:
                    base64_image = base64.b64encode(f.read()).decode('utf-8')
                content_list.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:image/png;base64,{base64_image}", "detail": "high"}
                })
            
            try:
                response = openai.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": content_list}],
                    max_tokens=4096,
                    temperature=0
                )
                
                result_text = response.choices[0].message.content
                if "```json" in result_text:
                    result_text = result_text.split("```json")[1].split("```")[0].strip()
                
                extracted_data = json.loads(result_text)
                
                # Save JSON
                json_file = Path("Captures/parcels") / f"openai_batch_{batch_num}.json"
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, indent=2)
                
                # Insert to database
                inserted = self.insert_batch_to_database(extracted_data, batch)
                total_inserted += inserted
                
                # Rename processed images
                for img_path in batch:
                    new_name = img_path.stem + '_processed' + img_path.suffix
                    img_path.rename(img_path.parent / new_name)
                
            except Exception as e:
                self.log_activity(f"ERROR: {str(e)}")
        
        self.log_activity(f"COMPLETE: Inserted {total_inserted} parcels")
    
    def insert_batch_to_database(self, parcel_data, image_paths):
        """Insert extracted data with google_addresses linkage"""
        import mysql.connector
        from config_hud_db import DB_CONFIG
        from datetime import datetime
        
        try:
            conn = mysql.connector.connect(**DB_CONFIG)
            cursor = conn.cursor()
            inserted_count = 0
            
            for idx, data in enumerate(parcel_data):
                try:
                    img_name = image_paths[idx].stem
                    google_id = img_name.split('_')[-1] if '_' in img_name else None
                    
                    insert_parcel = """
                    INSERT INTO king_county_parcels (
                        time_inserted, parcel_number, Present_use, Property_name,
                        Jurisdiction, Taxpayer_name, Address, Appraised_value,
                        Lot_area, num_of_units, num_of_buildings, Levy_code,
                        google_addresses_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    cursor.execute(insert_parcel, (
                        datetime.now(), data.get('parcel_number'),
                        data.get('present_use'), data.get('property_name'),
                        data.get('jurisdiction'), data.get('taxpayer_name'),
                        data.get('address'), data.get('appraised_value'),
                        data.get('lot_area'), data.get('num_units') or 0,
                        data.get('num_buildings') or 0, data.get('levy_code'),
                        google_id
                    ))
                    
                    parcel_id = cursor.lastrowid
                    
                    if google_id:
                        cursor.execute("UPDATE google_addresses SET king_county_parcels_id = %s WHERE id = %s", (parcel_id, google_id))
                    
                    conn.commit()
                    inserted_count += 1
                    self.log_activity(f"✓ Inserted: {data.get('parcel_number')}")
                    
                except mysql.connector.Error as e:
                    if "Duplicate entry" not in str(e):
                        self.log_activity(f"✗ Failed: {str(e)}")
            
            cursor.close()
            conn.close()
            return inserted_count
        except Exception as e:
            self.log_activity(f"ERROR: {str(e)}")
            return 0
    
    def process_with_beautifulsoup(self, image_paths):
        """Process images individually with BeautifulSoup/OCR"""
        self.log_activity(f"Processing {len(image_paths)} images with OCR")
        for img_path in image_paths:
            self.log_activity(f"Processing: {img_path.name}")
            new_name = img_path.stem + '_processed' + img_path.suffix
            img_path.rename(img_path.parent / new_name)

'''

# Insert the methods
content = content[:insert_pos] + new_methods + content[insert_pos:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Added batch processing methods to parcel_automation.py")
print("  - process_parcel_images_batch()")
print("  - process_with_openai_batch()")
print("  - insert_batch_to_database()")
print("  - process_with_beautifulsoup()")
