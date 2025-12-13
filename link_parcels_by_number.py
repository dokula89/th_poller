#!/usr/bin/env python3
"""
Link existing king_county_parcels to google_addresses using parcel_number from JSON files
This script reads all openai_batch_*.json files and links parcels to addresses
"""

import mysql.connector
import json
from pathlib import Path

# Database config
DB_CONFIG = {
    'host': '172.104.206.182',
    'port': 3306,
    'user': 'seattlelisted_usr',
    'password': 'T@5z6^pl}',
    'database': 'offta'
}

def link_parcels_from_json(verbose=None):
    """Link parcels to google_addresses using saved JSON files
    
    Args:
        verbose: If True, print output. If None, only print when run directly.
    """
    # Default to verbose when run as main script
    if verbose is None:
        verbose = __name__ == "__main__"
    
    parcels_dir = Path(r"C:\Users\dokul\Desktop\robot\th_poller\Captures\parcels")
    
    # Find all JSON files
    json_files = sorted(parcels_dir.glob("openai_batch_*.json"))
    if verbose:
        print(f"Found {len(json_files)} JSON files to process")
    
    if not json_files:
        if verbose:
            print("No JSON files found!")
        return {'linked': 0, 'already_linked': 0, 'not_found': 0}
    
    # Connect to database
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    total_linked = 0
    total_not_found = 0
    total_already_linked = 0
    
    for json_file in json_files:
        if verbose:
            print(f"\n📁 Processing: {json_file.name}")
        
        try:
            with open(json_file, 'r') as f:
                records = json.load(f)
        except Exception as e:
            if verbose:
                print(f"   ❌ Failed to read: {e}")
            continue
        
        for record in records:
            parcel_number = record.get('parcel_number')
            google_addr_id = record.get('google_addresses_id')
            
            if not parcel_number or not google_addr_id:
                continue
            
            # Check if already linked
            cursor.execute("""
                SELECT king_county_parcels_id FROM google_addresses WHERE id = %s
            """, (google_addr_id,))
            ga_row = cursor.fetchone()
            
            if ga_row and ga_row['king_county_parcels_id']:
                total_already_linked += 1
                continue  # Already linked
            
            # Find parcel by parcel_number
            cursor.execute("""
                SELECT id, google_addresses_id FROM king_county_parcels WHERE parcel_number = %s
            """, (parcel_number,))
            parcel_row = cursor.fetchone()
            
            if not parcel_row:
                if verbose:
                    print(f"   ❌ Parcel {parcel_number} not found in database (google_addr={google_addr_id})")
                total_not_found += 1
                continue
            
            parcel_id = parcel_row['id']
            
            # Link bidirectionally
            try:
                # Update google_addresses.king_county_parcels_id
                cursor.execute("""
                    UPDATE google_addresses SET king_county_parcels_id = %s WHERE id = %s
                """, (parcel_id, google_addr_id))
                
                # Update king_county_parcels.google_addresses_id
                cursor.execute("""
                    UPDATE king_county_parcels SET google_addresses_id = %s WHERE id = %s
                """, (google_addr_id, parcel_id))
                
                conn.commit()
                total_linked += 1
                if verbose:
                    print(f"   ✅ Linked: google_addresses.id={google_addr_id} ↔ king_county_parcels.id={parcel_id} (parcel: {parcel_number})")
                
            except Exception as e:
                if verbose:
                    print(f"   ❌ Failed to link: {e}")
    
    cursor.close()
    conn.close()
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"✅ COMPLETE:")
        print(f"   🔗 Newly linked: {total_linked}")
        print(f"   ⏭️  Already linked: {total_already_linked}")
        print(f"   ❌ Not found: {total_not_found}")
        print(f"{'='*60}")
    
    # Return results for programmatic use
    return {
        'linked': total_linked,
        'already_linked': total_already_linked,
        'not_found': total_not_found
    }

if __name__ == "__main__":
    link_parcels_from_json()
