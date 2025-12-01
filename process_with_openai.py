"""
Process parcel images with OpenAI Vision API and insert into database
Processes images in batches of 20, extracts structured data, and saves to MySQL
"""

import os
import json
import base64
import mysql.connector
from pathlib import Path
from datetime import datetime
import openai
from track_openai_costs import log_openai_cost

# OpenAI API key (set in environment variable)
openai.api_key = os.getenv('OPENAI_API_KEY')

def encode_image(image_path):
    """Encode image to base64 for OpenAI API"""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_with_openai(image_paths):
    """
    Send images to OpenAI Vision API for structured data extraction
    Returns list of extracted parcel data
    """
    print(f"\n📤 Sending {len(image_paths)} images to OpenAI Vision API...")
    
    # Prepare messages with all images
    content = [
        {
            "type": "text",
            "text": """Extract the following fields from each King County parcel viewer popup image:

Required fields:
- parcel_number: The parcel ID number
- present_use: Property use type (e.g., "Apartment", "Commercial")
- property_name: Name of the property
- jurisdiction: City/jurisdiction (e.g., SEATTLE, BELLEVUE)
- taxpayer_name: Name of the taxpayer
- address: Street address
- appraised_value: Property value in dollars (number only, no $)
- lot_area: Lot size in square feet
- levy_code: 4-digit levy code
- num_units: Number of units (numeric)
- num_buildings: Number of buildings (numeric)

Return a JSON array with one object per image, using these exact field names.
If a field is not visible or unclear, use null.
For numeric fields, extract only the number (no commas or special characters).

Example output format:
[
  {
    "parcel_number": "1142000875",
    "present_use": "Apartment",
    "property_name": "CELEBRITY PLACE 2",
    "jurisdiction": "SEATTLE",
    "taxpayer_name": "CLASSIC PROPERTIES LLC",
    "address": "4225 11TH AVE NE 98106",
    "appraised_value": "2473000",
    "lot_area": "4120",
    "levy_code": "0013",
    "num_units": "8",
    "num_buildings": "1"
  }
]"""
        }
    ]
    
    # Add each image with progress tracking
    import time
    start_time = time.time()
    for idx, img_path in enumerate(image_paths, 1):
        base64_image = encode_image(img_path)
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/png;base64,{base64_image}",
                "detail": "high"
            }
        })
        # Show progress
        progress = int((idx / len(image_paths)) * 100)
        print(f"\r💾 Encoding images: {idx}/{len(image_paths)} ({progress}%)", end='', flush=True)
    
    encode_time = time.time() - start_time
    print(f"\n✅ All images encoded in {encode_time:.1f}s")
    
    # Call OpenAI API with time tracking
    try:
        print(f"🔄 Sending to OpenAI API... (estimated time: {len(image_paths) * 2}s)")
        api_start = time.time()
        
        response = openai.chat.completions.create(
            model="gpt-4o",  # Use GPT-4 with vision
            messages=[
                {
                    "role": "user",
                    "content": content
                }
            ],
            max_tokens=4096,
            temperature=0  # Deterministic for data extraction
        )
        
        api_time = time.time() - api_start
        print(f"✅ OpenAI response received in {api_time:.1f}s")
        
        # Track API usage
        try:
            from track_api_usage import log_openai_call
            usage = response.usage
            log_openai_call(
                model="gpt-4o",
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
                endpoint="chat.completions",
                metadata={
                    "images_processed": len(image_paths),
                    "response_time": api_time
                }
            )
        except Exception as track_err:
            print(f"⚠️ API tracking failed: {track_err}")
        
        # Extract JSON from response
        print("📝 Parsing response...")
        result_text = response.choices[0].message.content
        
        # Parse JSON (may be wrapped in markdown code blocks)
        if "```json" in result_text:
            result_text = result_text.split("```json")[1].split("```")[0].strip()
        elif "```" in result_text:
            result_text = result_text.split("```")[1].split("```")[0].strip()
        
        extracted_data = json.loads(result_text)
        
        total_time = time.time() - start_time
        print(f"✅ OpenAI extracted data from {len(extracted_data)} images in {total_time:.1f}s total")
        print(f"   ⏱️ Average: {total_time/len(extracted_data):.1f}s per image")
        return extracted_data
        
    except Exception as e:
        print(f"❌ OpenAI API error: {str(e)}")
        return []

def insert_to_database(parcel_data):
    """Insert extracted parcel data into MySQL database"""
    
    try:
        # Import database config
        from config_hud_db import DB_CONFIG
        
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print(f"\n💾 Inserting {len(parcel_data)} parcels into database...")
        
        inserted_count = 0
        failed_count = 0
        
        for data in parcel_data:
            try:
                # Prepare insert query
                insert_query = """
                INSERT INTO king_county_parcels (
                    time_inserted,
                    parcel_number,
                    Present_use,
                    Property_name,
                    Jurisdiction,
                    Taxpayer_name,
                    Address,
                    Appraised_value,
                    Lot_area,
                    num_of_units,
                    num_of_buildings,
                    Levy_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                values = (
                    datetime.now(),
                    data.get('parcel_number'),
                    data.get('present_use'),
                    data.get('property_name'),
                    data.get('jurisdiction'),
                    data.get('taxpayer_name'),
                    data.get('address'),
                    data.get('appraised_value'),
                    data.get('lot_area'),
                    data.get('num_units') or 0,  # Default to 0 if null
                    data.get('num_buildings') or 0,  # Default to 0 if null
                    data.get('levy_code')
                )
                
                cursor.execute(insert_query, values)
                parcel_id = cursor.lastrowid  # Get the inserted parcel ID
                inserted_count += 1
                print(f"  ✅ MySQL INSERT: Parcel {data.get('parcel_number')} - {data.get('property_name')} - {data.get('jurisdiction')}")
                print(f"      Address: {data.get('address')} | Value: ${data.get('appraised_value')} | Units: {data.get('num_units')}")
                print(f"      Parcel ID: {parcel_id}")
                
                # Store the parcel number and ID for linking
                data['_db_id'] = parcel_id
                
            except mysql.connector.Error as e:
                error_msg = str(e)
                # Check if it's a duplicate key error
                if "Duplicate entry" in error_msg:
                    print(f"  ⏭️ MySQL SKIP: Parcel {data.get('parcel_number')} already exists in database")
                else:
                    failed_count += 1
                    print(f"  ❌ MySQL ERROR: Failed to insert {data.get('parcel_number')}: {error_msg}")
        
        # Commit all inserts
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ Database insert complete: {inserted_count} inserted, {failed_count} failed")
        return inserted_count
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return 0

def link_addresses_to_parcels(image_files, parcel_data):
    """Link google_addresses to king_county_parcels using image filenames"""
    
    try:
        # Import database config
        from config_hud_db import DB_CONFIG
        
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print(f"\n🔗 Linking {len(image_files)} addresses to parcels...")
        
        linked_count = 0
        
        for img_file, parcel in zip(image_files, parcel_data):
            # Extract google_addresses ID from filename: parcels_296.png -> 296
            filename = img_file.stem
            if filename.startswith('parcels_'):
                google_address_id = int(filename.replace('parcels_', '').replace('_processed', ''))
                parcel_db_id = parcel.get('_db_id')
                
                if parcel_db_id:
                    try:
                        # Update google_addresses with king_county_parcels_id
                        update_google = """
                        UPDATE google_addresses 
                        SET king_county_parcels_id = %s
                        WHERE id = %s
                        """
                        cursor.execute(update_google, (parcel_db_id, google_address_id))
                        
                        # Also update king_county_parcels with google_addresses_id
                        update_parcel = """
                        UPDATE king_county_parcels
                        SET google_addresses_id = %s
                        WHERE id = %s
                        """
                        cursor.execute(update_parcel, (google_address_id, parcel_db_id))
                        
                        linked_count += 1
                        print(f"  🔗 Linked google_addresses.id={google_address_id} ↔ king_county_parcels.id={parcel_db_id}")
                    except mysql.connector.Error as e:
                        print(f"  ❌ Failed to link address {google_address_id}: {e}")
        
        # Commit all links
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ Linking complete: {linked_count} addresses linked to parcels")
        return linked_count
        
    except Exception as e:
        print(f"❌ Linking error: {str(e)}")
        return 0

def process_parcel_images():
    """Main function to process parcel images with OpenAI and insert to database"""
    
    parcels_dir = Path("Captures/parcels")
    
    # Find all PNG images that are NOT already processed (exclude _processed, _skipped, and DEBUG)
    all_images = list(parcels_dir.glob("parcels_*.png"))
    image_files = sorted([img for img in all_images 
                         if not img.stem.endswith('_processed') 
                         and not img.stem.endswith('_skipped')
                         and not img.stem.startswith('DEBUG_')])
    
    if not image_files:
        print("❌ No unprocessed PNG images found in Captures/parcels/")
        return
    
    print(f"📁 Found {len(image_files)} unprocessed parcel images")
    
    # Check for OpenAI API key
    if not openai.api_key:
        print("❌ OPENAI_API_KEY environment variable not set!")
        print("   Set it with: $env:OPENAI_API_KEY='your-api-key-here'")
        return
    
    # Process in batches of 20
    batch_size = 20
    total_inserted = 0
    
    for i in range(0, len(image_files), batch_size):
        batch = image_files[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(image_files) + batch_size - 1) // batch_size
        
        print(f"\n{'='*60}")
        print(f"📦 Processing batch {batch_num}/{total_batches} ({len(batch)} images)")
        print(f"{'='*60}")
        
        # Extract with OpenAI
        extracted_data = extract_with_openai(batch)
        
        if extracted_data:
            # Log OpenAI API cost for this batch
            cost = log_openai_cost(len(batch))
            print(f"💵 API cost for batch: ${cost:.4f} (${cost/len(batch):.4f} per image)")
            
            # Save batch results to JSON
            batch_file = parcels_dir / f"openai_batch_{batch_num}.json"
            try:
                with open(batch_file, 'w', encoding='utf-8') as f:
                    json.dump(extracted_data, f, indent=2)
                print(f"💾 Saved batch results to: {batch_file.absolute()}")
                
                # Verify JSON file was created and has content
                if not batch_file.exists():
                    print(f"❌ ERROR: JSON file was not created at {batch_file.absolute()}")
                    print("❌ STOPPING: Cannot proceed without JSON results")
                    import sys
                    sys.exit(1)
                
                file_size = batch_file.stat().st_size
                if file_size == 0:
                    print(f"❌ ERROR: JSON file is empty at {batch_file.absolute()}")
                    print("❌ STOPPING: Cannot proceed with empty JSON")
                    import sys
                    sys.exit(1)
                    
                print(f"✅ JSON verified: {file_size} bytes")
                
            except Exception as json_err:
                print(f"❌ ERROR: Failed to save JSON: {json_err}")
                print("❌ STOPPING: Cannot proceed without JSON results")
                import sys
                sys.exit(1)
            
            # Insert into database
            print(f"\n📊 Starting MySQL insertion for batch {batch_num}...")
            inserted = insert_to_database(extracted_data)
            total_inserted += inserted
            print(f"✅ MySQL insertion complete for batch {batch_num}")
            
            # Link google_addresses to king_county_parcels
            linked = link_addresses_to_parcels(batch, extracted_data)
            print(f"✅ Linked {linked} addresses to parcels")
            
            # Rename processed images to mark them as complete
            print(f"\n📝 Marking {len(batch)} images as processed...")
            for img_path in batch:
                try:
                    processed_path = img_path.parent / f"{img_path.stem}_processed.png"
                    img_path.rename(processed_path)
                    print(f"  ✓ Renamed: {img_path.name} → {processed_path.name}")
                except Exception as rename_err:
                    print(f"  ⚠️  Failed to rename {img_path.name}: {rename_err}")
        else:
            print(f"⚠️ No data extracted from batch {batch_num}")
            print("❌ ERROR: OpenAI returned no data")
            print("❌ STOPPING: Cannot proceed without extraction results")
            import sys
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"🎉 COMPLETE: Processed {len(image_files)} images")
    print(f"   Total inserted to database: {total_inserted}")
    print(f"{'='*60}")

if __name__ == "__main__":
    # Set stdout to UTF-8 encoding to handle emojis
    import sys
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    process_parcel_images()
