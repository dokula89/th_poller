#!/usr/bin/env python3
"""
Clear all rows from apartment_listings table
Also clears price_changes table first due to foreign key constraint
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
    # Count existing rows
    cursor.execute("SELECT COUNT(*) FROM apartment_listings")
    count_listings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM apartment_listings_price_changes")
    count_changes = cursor.fetchone()[0]
    
    print(f"Current rows in apartment_listings: {count_listings}")
    print(f"Current rows in apartment_listings_price_changes: {count_changes}")
    print()
    
    if count_changes > 0:
        print("Clearing apartment_listings_price_changes first...")
        cursor.execute("DELETE FROM apartment_listings_price_changes")
        conn.commit()
        print(f"✅ Deleted {count_changes} price change rows")
    
    if count_listings > 0:
        print("Clearing apartment_listings...")
        cursor.execute("DELETE FROM apartment_listings")
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM apartment_listings")
        after_delete = cursor.fetchone()[0]
        print(f"✅ Deleted {count_listings - after_delete} listing rows")
        
        if after_delete > 0:
            print(f"⚠️ Warning: {after_delete} rows remain after DELETE")
            print("Trying with SET FOREIGN_KEY_CHECKS=0...")
            
            cursor.execute("SET FOREIGN_KEY_CHECKS=0")
            cursor.execute("DELETE FROM apartment_listings")
            cursor.execute("SET FOREIGN_KEY_CHECKS=1")
            conn.commit()
            
            cursor.execute("SELECT COUNT(*) FROM apartment_listings")
            final = cursor.fetchone()[0]
            print(f"After forced delete: {final} rows remain")
    else:
        print("ℹ️ apartment_listings table is already empty")
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM apartment_listings")
    final_count = cursor.fetchone()[0]
    print(f"\n✅ apartment_listings now has {final_count} rows")

except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
