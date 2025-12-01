"""
Clean unit numbers from existing google_addresses table entries
This will strip apartment/unit numbers from addresses already in the database
"""

import mysql.connector
import re

def strip_unit_from_address(address):
    """Remove unit numbers from address"""
    if not address:
        return address
    
    # Remove patterns like: #34, Unit 123, Apt A, Suite X, space+digits at end, etc.
    patterns = [
        r'\s+\d{1,4}(?:A|B|C|D)?,\s+',  # " 334, " or " 101, " before city
        r'\s+-\s*\d+[A-Za-z]?,\s+',  # " - 00A, " before city
        r'\s*#\d+.*$',  # #34 at end
        r'\s*Unit\s+[A-Za-z0-9]+.*$',  # Unit 123
        r'\s*Apt\.?\s+[A-Za-z0-9]+.*$',  # Apt A or Apt. A
        r'\s*Suite\s+[A-Za-z0-9]+.*$',  # Suite X
        r'\s*Ste\.?\s+[A-Za-z0-9]+.*$',  # Ste X
        r',\s*Apt\.?\s+[A-Za-z0-9]+',  # , Apt 302
        r'\s+[A-Za-z]?\d{2,4}[A-Za-z]?$',  # Space followed by 2-4 digits at very end
    ]
    
    cleaned = address
    for pattern in patterns:
        cleaned = re.sub(pattern, ', ' if ', ' in pattern else '', cleaned, flags=re.IGNORECASE)
    
    return cleaned.strip()


def main():
    """Clean all addresses in google_addresses table"""
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host='127.0.0.1',
            user='root',
            password='',
            database='offta'
        )
        cursor = conn.cursor(dictionary=True)
        
        print("🔍 Fetching addresses from google_addresses table...")
        
        # Get all addresses with json_dump (extract formatted_address from JSON)
        cursor.execute("""
            SELECT 
                id,
                place_id,
                COALESCE(
                    JSON_UNQUOTE(JSON_EXTRACT(json_dump, '$.result.formatted_address')),
                    JSON_UNQUOTE(JSON_EXTRACT(json_dump, '$.result.name')),
                    JSON_UNQUOTE(JSON_EXTRACT(json_dump, '$.result.vicinity'))
                ) as current_address
            FROM google_addresses
            WHERE json_dump IS NOT NULL
        """)
        
        addresses = cursor.fetchall()
        print(f"✓ Found {len(addresses)} addresses to check\n")
        
        cleaned_count = 0
        unchanged_count = 0
        
        # Process each address
        for addr in addresses:
            original = addr['current_address']
            if not original:
                unchanged_count += 1
                continue
                
            cleaned = strip_unit_from_address(original)
            
            if cleaned != original:
                print(f"🧹 ID {addr['id']}:")
                print(f"   Before: {original}")
                print(f"   After:  {cleaned}")
                print()
                
                # Update the place_id or store cleaned address in a new column
                # For now, just count them
                cleaned_count += 1
            else:
                unchanged_count += 1
        
        print(f"\n{'='*60}")
        print(f"Summary:")
        print(f"  ✓ Addresses that would be cleaned: {cleaned_count}")
        print(f"  • Addresses unchanged: {unchanged_count}")
        print(f"  • Total addresses: {len(addresses)}")
        print(f"{'='*60}\n")
        
        # Ask for confirmation before updating
        response = input("Do you want to update the database? (yes/no): ").lower().strip()
        
        if response == 'yes':
            print("\n🔧 Updating database...")
            
            cursor.execute("""
                SELECT 
                    id,
                    place_id,
                    json_dump,
                    COALESCE(
                        JSON_UNQUOTE(JSON_EXTRACT(json_dump, '$.result.formatted_address')),
                        JSON_UNQUOTE(JSON_EXTRACT(json_dump, '$.result.name')),
                        JSON_UNQUOTE(JSON_EXTRACT(json_dump, '$.result.vicinity'))
                    ) as current_address
                FROM google_addresses
                WHERE json_dump IS NOT NULL
            """)
            
            addresses = cursor.fetchall()
            updated = 0
            
            for addr in addresses:
                original = addr['current_address']
                if not original:
                    continue
                    
                cleaned = strip_unit_from_address(original)
                
                if cleaned != original:
                    # Update json_dump with cleaned address
                    import json
                    json_data = json.loads(addr['json_dump'])
                    
                    if 'result' in json_data and 'formatted_address' in json_data['result']:
                        json_data['result']['formatted_address'] = cleaned
                        
                        cursor.execute("""
                            UPDATE google_addresses
                            SET json_dump = %s
                            WHERE id = %s
                        """, (json.dumps(json_data), addr['id']))
                        
                        updated += 1
                        if updated % 10 == 0:
                            print(f"  • Updated {updated} addresses...")
            
            conn.commit()
            print(f"\n✅ Successfully updated {updated} addresses!")
        else:
            print("\n❌ Database update cancelled.")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
