"""
Enhanced parcel automation with OpenAI and BeautifulSoup extraction methods
Handles batch processing, image renaming, and cross-referencing between tables
"""

import os
import json
import base64
from pathlib import Path
from datetime import datetime
import mysql.connector
import openai

# Set OpenAI API key from environment
openai.api_key = os.getenv('OPENAI_API_KEY')

def count_unprocessed_images(parcels_dir):
    """Count images that haven't been processed yet"""
    all_images = list(Path(parcels_dir).glob("parcels_*.png"))
    processed_images = list(Path(parcels_dir).glob("parcels_*_processed.png"))
    unprocessed = [img for img in all_images if not str(img).endswith('_processed.png')]
    return len(unprocessed), unprocessed

def rename_processed_image(image_path):
    """Rename image to mark it as processed"""
    if '_processed' not in str(image_path):
        new_name = image_path.stem + '_processed' + image_path.suffix
        new_path = image_path.parent / new_name
        image_path.rename(new_path)
        return new_path
    return image_path

def extract_with_openai_batch(image_paths, batch_num):
    """Extract data from images using OpenAI Vision API"""
    print(f"\n📤 Sending {len(image_paths)} images to OpenAI Vision API (Batch {batch_num})...")
    
    # Encode all images
    content = [
        {
            "type": "text",
            "text": """Extract the following fields from each King County parcel viewer popup image (orange background with white text):

Required fields:
- parcel_number: The parcel ID number
- present_use: Property use type (e.g., "Apartment", "Commercial")
- property_name: Name of the property
- jurisdiction: City/jurisdiction (e.g., SEATTLE, BELLEVUE)
- taxpayer_name: Name of the taxpayer
- address: Street address
- appraised_value: Property value in dollars (number only, no $ or commas)
- lot_area: Lot size in square feet (number only, no commas)
- levy_code: 4-digit levy code
- num_units: Number of units (numeric only)
- num_buildings: Number of buildings (numeric only)

Return a JSON array with one object per image, using these exact field names.
If a field is not visible, use null.
Extract only numbers for numeric fields.

Example:
[
  {
    "parcel_number": "1142000875",
    "present_use": "Apartment",
    "property_name": "CELEBRITY PLACE 2",
    "jurisdiction": "SEATTLE",
    "taxpayer_name": "CLASSIC PROPERTIES LLC",
    "address": "4225 11TH AVE NE",
    "appraised_value": "2473000",
    "lot_area": "4120",
    "levy_code": "0013",
    "num_units": "8",
    "num_buildings": "1"
  }
]"""
        }
    ]
    
    # Add images
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
        
        extracted_data = json.loads(result_text)
        print(f"✅ OpenAI extracted {len(extracted_data)} parcels")
        
        return extracted_data
        
    except Exception as e:
        print(f"❌ OpenAI API error: {str(e)}")
        return []

def insert_to_database_with_linking(parcel_data_list, google_addresses_id=None):
    """
    Insert parcel data and create cross-references between tables
    - Inserts into king_county_parcels
    - Links to google_addresses via google_addresses_id
    - Updates google_addresses with king_county_parcels_id
    """
    try:
        from config_hud_db import DB_CONFIG
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print(f"\n💾 Inserting {len(parcel_data_list)} parcels with cross-references...")
        
        inserted_count = 0
        skipped_count = 0
        
        for data in parcel_data_list:
            try:
                # Insert into king_county_parcels
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
                    Levy_code,
                    google_addresses_id
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                    data.get('num_units') or 0,
                    data.get('num_buildings') or 0,
                    data.get('levy_code'),
                    google_addresses_id
                )
                
                cursor.execute(insert_query, values)
                parcel_id = cursor.lastrowid
                
                # Update google_addresses with king_county_parcels_id
                if google_addresses_id and parcel_id:
                    update_query = """
                    UPDATE google_addresses 
                    SET king_county_parcels_id = %s 
                    WHERE id = %s
                    """
                    cursor.execute(update_query, (parcel_id, google_addresses_id))
                
                inserted_count += 1
                print(f"  ✓ Inserted: {data.get('parcel_number')} - {data.get('property_name')}")
                
            except mysql.connector.Error as e:
                if "Duplicate entry" in str(e):
                    skipped_count += 1
                    print(f"  ⚠️  Skipped (exists): {data.get('parcel_number')}")
                else:
                    print(f"  ✗ Error: {data.get('parcel_number')} - {str(e)}")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"\n✅ Complete: {inserted_count} inserted, {skipped_count} skipped")
        return inserted_count
        
    except Exception as e:
        print(f"❌ Database error: {str(e)}")
        return 0

def process_with_openai(parcels_dir, min_batch_size=20):
    """
    Process parcel images with OpenAI when batch threshold is reached
    """
    unprocessed_count, unprocessed_images = count_unprocessed_images(parcels_dir)
    
    print(f"\n📊 Found {unprocessed_count} unprocessed parcel images")
    
    if unprocessed_count < min_batch_size:
        print(f"⏳ Waiting for {min_batch_size} images. Current: {unprocessed_count}")
        print(f"   Need {min_batch_size - unprocessed_count} more images to process batch")
        return None
    
    if not openai.api_key:
        print("❌ OPENAI_API_KEY not set!")
        return None
    
    # Process in batches of 20
    batch_size = 20
    total_inserted = 0
    
    for i in range(0, len(unprocessed_images), batch_size):
        batch = unprocessed_images[i:i+batch_size]
        batch_num = (i // batch_size) + 1
        
        print(f"\n{'='*60}")
        print(f"📦 Processing OpenAI Batch {batch_num} ({len(batch)} images)")
        print(f"{'='*60}")
        
        # Extract with OpenAI
        extracted_data = extract_with_openai_batch(batch, batch_num)
        
        if extracted_data:
            # Save JSON
            json_file = Path(parcels_dir) / f"openai_batch_{batch_num}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(extracted_data, f, indent=2)
            print(f"💾 Saved: {json_file}")
            
            # Insert to database
            inserted = insert_to_database_with_linking(extracted_data)
            total_inserted += inserted
            
            # Rename processed images
            for img in batch:
                rename_processed_image(img)
                print(f"  📝 Renamed: {img.name} → {img.stem}_processed{img.suffix}")
    
    print(f"\n🎉 Total inserted: {total_inserted} parcels")
    return total_inserted

def process_with_beautifulsoup(ocr_text):
    """
    Process OCR text with pattern matching (original method)
    This is the fallback method or for single-image processing
    """
    import re
    
    patterns = {
        'parcel_number': [
            r'[Pp]arc[ae]l[:\s]+([0-9A-Z]+)',
            r'([0-9A-Z]{9,10})',
        ],
        'present_use': [
            r'[Pp]reseamtuse[:\s]*([^\n]+)',
            r'[Pp]resent\s*use[:\s]*([^\n]+)',
        ],
        'property_name': [
            r'[Pp]roperty\s*name[:\s]*([A-Z][^\n]+(?:\n[A-Z][^\n]+)?)',
        ],
        'jurisdiction': [
            r'[Aa]raacdion[:\s.]*([^\n]+)',
            r'[Jj]uradiction[:\s]*([^\n]+)',
            r'(SEATTLE|BELLEVUE|RENTON|KENT|AUBURN)',
        ],
        'taxpayer_name': [
            r'[Tt]axpayer\s+name[:\s]+(.+)',
        ],
        'address': [
            r'[Aa]ddress[:\s]*([^\n]+)',
        ],
        'appraised_value': [
            r'[Aa]ppraised\s*value[:\s]*\$?([\d,]+)',
        ],
        'lot_area': [
            r'[Ll]otarea[:\s]*([\d,\.]+)',
            r'[Ll]ot\s*area[:\s]*([\d,\.]+)',
        ],
        'levy_code': [
            r'[Ll]avy\s*code[:\s]+([O0-9]{3,4})',
        ],
        'num_units': [
            r'[Zz]at\s*unts[:\s]+(\d+)',
            r'#ot\s*unts[:\s]+([\d]+)',
            r'#\s*of\s*units[:\s]+([\d]+)',
        ],
        'num_buildings': [
            r'[Kk]oto[il]lings[:\s]+([\d]+)',
            r'#\s*of\s*buildings[:\s]+([\d]+)',
        ],
    }
    
    extracted = {}
    for field, pattern_list in patterns.items():
        for pattern in pattern_list:
            match = re.search(pattern, ocr_text, re.IGNORECASE)
            if match:
                extracted[field] = match.group(1).strip()
                break
    
    return extracted

if __name__ == "__main__":
    parcels_dir = Path("Captures/parcels")
    process_with_openai(parcels_dir, min_batch_size=20)
