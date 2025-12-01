"""
Link existing king_county_parcels records to google_addresses
This script processes already-processed parcel images and creates the links
"""

import mysql.connector
from pathlib import Path
from config_hud_db import DB_CONFIG

def link_existing_parcels():
    """Link existing parcels to google_addresses using processed image filenames"""
    
    parcels_dir = Path("Captures/parcels")
    
    # Find all processed images
    processed_images = list(parcels_dir.glob("parcels_*_processed.png"))
    
    if not processed_images:
        print("❌ No processed images found")
        return
    
    print(f"📁 Found {len(processed_images)} processed images")
    
    # Connect to database
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    linked_count = 0
    already_linked = 0
    not_found = 0
    
    for img_file in processed_images:
        # Extract google_addresses ID from filename: parcels_296_processed.png -> 296
        filename = img_file.stem
        google_address_id = int(filename.replace('parcels_', '').replace('_processed', ''))
        
        try:
            # Check if already linked
            cursor.execute("""
                SELECT king_county_parcels_id 
                FROM google_addresses 
                WHERE id = %s
            """, (google_address_id,))
            result = cursor.fetchone()
            
            if not result:
                print(f"  ⚠️  Address ID {google_address_id} not found in database")
                not_found += 1
                continue
            
            if result['king_county_parcels_id']:
                print(f"  ⏭️  Address ID {google_address_id} already linked to parcel {result['king_county_parcels_id']}")
                already_linked += 1
                continue
            
            # Get the address to find matching parcel
            cursor.execute("""
                SELECT json_dump 
                FROM google_addresses 
                WHERE id = %s
            """, (google_address_id,))
            addr_data = cursor.fetchone()
            
            if not addr_data or not addr_data['json_dump']:
                print(f"  ⚠️  No address data for ID {google_address_id}")
                not_found += 1
                continue
            
            # Parse address from JSON
            import json
            json_data = json.loads(addr_data['json_dump'])
            address_text = (
                json_data.get('result', {}).get('formatted_address') or
                json_data.get('result', {}).get('name') or
                ''
            )
            
            if not address_text:
                print(f"  ⚠️  No address text for ID {google_address_id}")
                not_found += 1
                continue
            
            # Try to find matching parcel by address (partial match)
            # Extract just the street address part
            address_parts = address_text.split(',')
            street_address = address_parts[0].strip() if address_parts else address_text
            
            # Search for parcel with matching address
            cursor.execute("""
                SELECT id, parcel_number, Property_name, Address
                FROM king_county_parcels
                WHERE Address LIKE %s
                OR parcel_number LIKE %s
                ORDER BY time_inserted DESC
                LIMIT 1
            """, (f"%{street_address}%", f"%{google_address_id}%"))
            
            parcel = cursor.fetchone()
            
            if parcel:
                # Link them
                cursor.execute("""
                    UPDATE google_addresses 
                    SET king_county_parcels_id = %s
                    WHERE id = %s
                """, (parcel['id'], google_address_id))
                
                conn.commit()
                linked_count += 1
                print(f"  ✅ Linked address {google_address_id} → parcel {parcel['id']} ({parcel['parcel_number']})")
            else:
                print(f"  ⚠️  No matching parcel found for address ID {google_address_id} ({street_address})")
                not_found += 1
                
        except Exception as e:
            print(f"  ❌ Error processing address {google_address_id}: {e}")
    
    cursor.close()
    conn.close()
    
    print(f"\n{'='*60}")
    print(f"✅ Linking complete:")
    print(f"   🔗 Newly linked: {linked_count}")
    print(f"   ⏭️  Already linked: {already_linked}")
    print(f"   ⚠️  Not found/skipped: {not_found}")
    print(f"   📊 Total processed: {len(processed_images)}")
    print(f"{'='*60}")

if __name__ == "__main__":
    link_existing_parcels()
