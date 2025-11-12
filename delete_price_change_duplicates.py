#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Delete duplicate entries from apartment_listings_price_changes table.
Keep only the latest entry per apartment per day.
"""

import mysql.connector
from datetime import datetime

def delete_duplicates():
    """Delete duplicate price change entries"""
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            database='offta',
            connect_timeout=10
        )
        cursor = conn.cursor()
        
        print("Analyzing apartment_listings_price_changes table...")
        
        # Get count before
        cursor.execute("SELECT COUNT(*) FROM apartment_listings_price_changes")
        count_before = cursor.fetchone()[0]
        print(f"Total entries before: {count_before}")
        
        # Find and delete duplicates - keep only the latest entry per apartment per day
        delete_query = """
            DELETE pc1 FROM apartment_listings_price_changes pc1
            INNER JOIN apartment_listings_price_changes pc2 
            WHERE pc1.apartment_listings_id = pc2.apartment_listings_id 
            AND DATE(pc1.time) = DATE(pc2.time) 
            AND pc1.time < pc2.time
        """
        
        print("Deleting duplicates (keeping latest entry per day per apartment)...")
        cursor.execute(delete_query)
        deleted = cursor.rowcount
        print(f"Deleted {deleted} duplicate entries")
        
        # Get count after
        cursor.execute("SELECT COUNT(*) FROM apartment_listings_price_changes")
        count_after = cursor.fetchone()[0]
        print(f"Total entries after: {count_after}")
        
        # Commit changes
        conn.commit()
        print("✓ Changes committed successfully")
        
        # Show some statistics
        cursor.execute("""
            SELECT apartment_listings_id, DATE(time) as date, COUNT(*) as count
            FROM apartment_listings_price_changes
            GROUP BY apartment_listings_id, DATE(time)
            HAVING count > 1
        """)
        remaining_dupes = cursor.fetchall()
        
        if remaining_dupes:
            print(f"\n⚠️ WARNING: Still found {len(remaining_dupes)} duplicate entries:")
            for dupe in remaining_dupes[:10]:  # Show first 10
                print(f"  - Apartment ID {dupe[0]} on {dupe[1]}: {dupe[2]} entries")
        else:
            print("\n✓ No duplicates found - table is clean!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    delete_duplicates()
