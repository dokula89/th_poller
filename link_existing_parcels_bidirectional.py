#!/usr/bin/env python3
"""
Link existing king_county_parcels to google_addresses bidirectionally
Updates both google_addresses.king_county_parcels_id and king_county_parcels.google_addresses_id
"""

import mysql.connector
from pathlib import Path
from config_hud_db import DB_CONFIG

def link_existing_parcels():
    """Find and link existing processed parcels to their google_addresses"""
    
    try:
        # Connect to database
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        
        # Get all processed parcel files
        parcels_dir = Path("Captures/parcels")
        processed_files = list(parcels_dir.glob("parcels_*_processed.png"))
        
        print(f"Found {len(processed_files)} processed parcel images")
        
        linked_count = 0
        not_found_count = 0
        
        for img_file in processed_files:
            # Extract google_addresses ID from filename: parcels_296_processed.png -> 296
            filename = img_file.stem.replace('parcels_', '').replace('_processed', '')
            
            try:
                google_address_id = int(filename)
            except ValueError:
                print(f"  ⚠️ Skipping invalid filename: {img_file.name}")
                continue
            
            # Get the address from google_addresses
            cursor.execute("""
                SELECT id, json_dump, king_county_parcels_id 
                FROM google_addresses 
                WHERE id = %s
            """, (google_address_id,))
            
            address_row = cursor.fetchone()
            
            if not address_row:
                print(f"  ❌ Address ID {google_address_id} not found in database")
                not_found_count += 1
                continue
            
            # Extract address from json_dump
            import json
            try:
                json_data = json.loads(address_row['json_dump'])
                full_address = json_data.get('formatted_address', '')
                # Clean address for matching
                address_clean = full_address.replace(', USA', '').strip()
            except:
                print(f"  ⚠️ Could not parse JSON for address ID {google_address_id}")
                continue
            
            # Find matching parcel by address
            cursor.execute("""
                SELECT id, Address, google_addresses_id
                FROM king_county_parcels 
                WHERE Address LIKE %s
                LIMIT 1
            """, (f"%{address_clean}%",))
            
            parcel_row = cursor.fetchone()
            
            if parcel_row:
                parcel_id = parcel_row['id']
                
                # Update google_addresses.king_county_parcels_id
                cursor.execute("""
                    UPDATE google_addresses 
                    SET king_county_parcels_id = %s
                    WHERE id = %s
                """, (parcel_id, google_address_id))
                
                # Update king_county_parcels.google_addresses_id
                cursor.execute("""
                    UPDATE king_county_parcels
                    SET google_addresses_id = %s
                    WHERE id = %s
                """, (google_address_id, parcel_id))
                
                conn.commit()
                
                linked_count += 1
                print(f"  ✅ Linked google_addresses.id={google_address_id} ↔ king_county_parcels.id={parcel_id}")
                print(f"      Address: {address_clean}")
            else:
                print(f"  ⚠️ No matching parcel found for address ID {google_address_id}: {address_clean}")
                not_found_count += 1
        
        cursor.close()
        conn.close()
        
        print(f"\n✅ Complete: {linked_count} linked, {not_found_count} not found")
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    link_existing_parcels()
