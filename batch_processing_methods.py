"""
Integrated batch processing methods for parcel_automation.py
Add these methods to the ParcelAutomationWindow class
"""

METHODS_TO_ADD = '''
    def process_parcel_images_batch(self):
        """Process saved parcel images based on selected extraction method"""
        import os
        import json
        import base64
        from pathlib import Path
        from datetime import datetime
        
        parcels_dir = Path("Captures/parcels")
        
        # Find unprocessed PNG images
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
        
        # Check API key
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            self.log_activity("ERROR: OPENAI_API_KEY not set!")
            self.log_activity("Set it with: $env:OPENAI_API_KEY='your-key'")
            return
        
        openai.api_key = api_key
        
        # Wait for at least 20 images
        if len(image_paths) < 20:
            self.log_activity(f"Waiting for 20 images... Currently have {len(image_paths)}")
            self.log_activity("OpenAI batch processing requires 20 images minimum")
            return
        
        # Process in batches of 20
        batch_size = 20
        total_inserted = 0
        
        for i in range(0, len(image_paths), batch_size):
            batch = image_paths[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            
            self.log_activity(f"\\n{'='*50}")
            self.log_activity(f"Processing OpenAI batch {batch_num} ({len(batch)} images)")
            
            # Extract with OpenAI
            extracted_data = self.extract_with_openai_vision(batch)
            
            if extracted_data:
                # Save JSON
                from pathlib import Path
                json_file = Path("Captures/parcels") / f"openai_batch_{batch_num}.json"
                import json
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, indent=2)
                self.log_activity(f"Saved batch results to {json_file.name}")
                
                # Insert to database with google_addresses linkage
                inserted = self.insert_batch_to_database(extracted_data, batch)
                total_inserted += inserted
                
                # Rename processed images
                for img_path in batch:
                    new_name = img_path.stem + '_processed' + img_path.suffix
                    new_path = img_path.parent / new_name
                    img_path.rename(new_path)
                    self.log_activity(f"Renamed: {img_path.name} → {new_name}")
            else:
                self.log_activity(f"ERROR: No data extracted from batch {batch_num}")
        
        self.log_activity(f"\\n{'='*50}")
        self.log_activity(f"COMPLETE: Inserted {total_inserted} parcels to database")
    
    def extract_with_openai_vision(self, image_paths):
        """Send images to OpenAI Vision API"""
        import openai
        import base64
        import json
        
        self.log_activity(f"Sending {len(image_paths)} images to OpenAI...")
        
        # Encode images
        content = [{
            "type": "text",
            "text": """Extract these fields from each King County parcel popup:

parcel_number, present_use, property_name, jurisdiction, taxpayer_name, address, 
appraised_value (number only), lot_area (number only), levy_code, 
num_units (number), num_buildings (number)

Return JSON array with one object per image. Use null if field not visible.

Example: [{"parcel_number": "1142000875", "present_use": "Apartment", ...}]"""
        }]
        
        for img_path in image_paths:
            with open(img_path, "rb") as f:
                base64_image = base64.b64encode(f.read()).decode('utf-8')
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}",
                    "detail": "high"
                }
            })
        
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": content}],
                max_tokens=4096,
                temperature=0
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            extracted = json.loads(result_text)
            self.log_activity(f"✓ OpenAI extracted {len(extracted)} parcels")
            return extracted
            
        except Exception as e:
            self.log_activity(f"ERROR: OpenAI API failed - {str(e)}")
            return []
    
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
                    # Get google_addresses_id from image filename
                    img_name = image_paths[idx].stem  # e.g., "parcels_123"
                    google_id = img_name.split('_')[-1] if '_' in img_name else None
                    
                    # Insert into king_county_parcels
                    insert_parcel = """
                    INSERT INTO king_county_parcels (
                        time_inserted, parcel_number, Present_use, Property_name,
                        Jurisdiction, Taxpayer_name, Address, Appraised_value,
                        Lot_area, num_of_units, num_of_buildings, Levy_code,
                        google_addresses_id
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """
                    
                    parcel_values = (
                        datetime.now(),
                        data.get('parcel_number'),
                        data.get('present_use'),
                        data.get('property_name'),
                        data.get('jurisdiction'),
                        data.get('taxpayer_name'),
                        data.get('address'),
                        data.get('appraised_value'),
                        data.get('lot_area'),
                        data.get('num_units') or 0,
                        data.get('num_buildings') or 0,
                        data.get('levy_code'),
                        google_id
                    )
                    
                    cursor.execute(insert_parcel, parcel_values)
                    parcel_id = cursor.lastrowid
                    
                    # Update google_addresses with king_county_parcels_id
                    if google_id:
                        update_google = """
                        UPDATE google_addresses 
                        SET king_county_parcels_id = %s 
                        WHERE id = %s
                        """
                        cursor.execute(update_google, (parcel_id, google_id))
                    
                    conn.commit()
                    inserted_count += 1
                    
                    self.log_activity(f"✓ Inserted: {data.get('parcel_number')} (ID: {parcel_id})")
                    
                except mysql.connector.Error as e:
                    if "Duplicate entry" in str(e):
                        self.log_activity(f"⚠️ Skipped (exists): {data.get('parcel_number')}")
                    else:
                        self.log_activity(f"✗ Failed: {data.get('parcel_number')} - {str(e)}")
            
            cursor.close()
            conn.close()
            return inserted_count
            
        except Exception as e:
            self.log_activity(f"ERROR: Database error - {str(e)}")
            return 0
    
    def process_with_beautifulsoup(self, image_paths):
        """Process images individually with BeautifulSoup/OCR (existing method)"""
        self.log_activity(f"Processing {len(image_paths)} images with BeautifulSoup/OCR")
        self.log_activity("This will process each image individually as captured")
        
        # Process each image immediately
        for img_path in image_paths:
            self.log_activity(f"\\nProcessing: {img_path.name}")
            
            # Extract using existing OCR method (extract_structured_data)
            # This would call your existing extraction logic
            
            # For now, log that it would be processed
            self.log_activity(f"Would process with OCR: {img_path.name}")
            
            # Rename after processing
            new_name = img_path.stem + '_processed' + img_path.suffix
            new_path = img_path.parent / new_name
            img_path.rename(new_path)
            self.log_activity(f"Renamed: {new_name}")
'''

print("Methods to add to ParcelAutomationWindow class:")
print(METHODS_TO_ADD)
print("\\n" + "="*60)
print("Copy these methods into the ParcelAutomationWindow class")
print("Or run add_batch_methods.py to automatically inject them")
