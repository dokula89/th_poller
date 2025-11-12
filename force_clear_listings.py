#!/usr/bin/env python3
"""
Force clear apartment_listings table with detailed debugging
"""

import mysql.connector

# Database connection
conn = mysql.connector.connect(
    host="172.104.206.182",
    user="seattlelisted_usr",
    password="T@5z6^pl}",
    database="offta",
    connection_timeout=10,
    use_pure=True
)

cursor = conn.cursor(buffered=True)

try:
    # Check initial count
    cursor.execute("SELECT COUNT(*) FROM apartment_listings")
    initial_count = cursor.fetchone()[0]
    print(f"Initial count in apartment_listings: {initial_count}")
    
    if initial_count == 0:
        print("✅ Table is already empty!")
    else:
        # Disable foreign key checks
        print("\nDisabling foreign key checks...")
        cursor.execute("SET FOREIGN_KEY_CHECKS=0")
        
        # Delete from price changes first
        print("Deleting from apartment_listings_price_changes...")
        cursor.execute("DELETE FROM apartment_listings_price_changes")
        affected = cursor.rowcount
        print(f"  Deleted {affected} rows from price_changes")
        
        # Delete from apartment_listings
        print("Deleting from apartment_listings...")
        cursor.execute("DELETE FROM apartment_listings")
        affected = cursor.rowcount
        print(f"  Deleted {affected} rows from apartment_listings")
        
        # Re-enable foreign key checks
        print("Re-enabling foreign key checks...")
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")
        
        # Commit
        conn.commit()
        print("✅ Changes committed")
        
        # Verify
        cursor.execute("SELECT COUNT(*) FROM apartment_listings")
        final_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM apartment_listings_price_changes")
        final_changes = cursor.fetchone()[0]
        
        print(f"\nFinal counts:")
        print(f"  apartment_listings: {final_count} rows")
        print(f"  apartment_listings_price_changes: {final_changes} rows")
        
        if final_count == 0:
            print("\n✅ SUCCESS! apartment_listings is now empty")
        else:
            print(f"\n❌ FAILED! {final_count} rows still remain")
            
            # Show sample of remaining rows
            print("\nSample of remaining rows:")
            cursor.execute("SELECT id, full_address FROM apartment_listings LIMIT 5")
            for row in cursor.fetchall():
                print(f"  ID {row[0]}: {row[1]}")

except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    cursor.close()
    conn.close()
