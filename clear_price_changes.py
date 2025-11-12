#!/usr/bin/env python3
"""
Clear all rows from apartment_listings_price_changes table
(DELETE instead of TRUNCATE to respect foreign key constraints)
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
    cursor.execute("SELECT COUNT(*) FROM apartment_listings_price_changes")
    count_before = cursor.fetchone()[0]
    
    print(f"Current rows in apartment_listings_price_changes: {count_before}")
    
    if count_before > 0:
        # Delete all rows (respects foreign key constraints)
        cursor.execute("DELETE FROM apartment_listings_price_changes")
        conn.commit()
        
        # Verify deletion
        cursor.execute("SELECT COUNT(*) FROM apartment_listings_price_changes")
        count_after = cursor.fetchone()[0]
        
        print(f"✅ Deleted {count_before - count_after} rows")
        print(f"Remaining rows: {count_after}")
    else:
        print("ℹ️ Table is already empty")

except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
