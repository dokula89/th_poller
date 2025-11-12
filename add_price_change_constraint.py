#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Add unique constraint to apartment_listings_price_changes table
to ensure only one entry per apartment per day.
"""

import mysql.connector

def add_unique_constraint():
    """Add unique constraint if it doesn't exist"""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            database='offta',
            connect_timeout=10
        )
        cursor = conn.cursor()
        
        print("Checking existing constraints on apartment_listings_price_changes...")
        
        # Check if constraint already exists
        cursor.execute("""
            SELECT CONSTRAINT_NAME 
            FROM information_schema.TABLE_CONSTRAINTS 
            WHERE TABLE_SCHEMA = 'offta' 
            AND TABLE_NAME = 'apartment_listings_price_changes' 
            AND CONSTRAINT_TYPE = 'UNIQUE'
        """)
        existing = cursor.fetchall()
        
        if existing:
            print(f"Found existing unique constraints: {[c[0] for c in existing]}")
        else:
            print("No unique constraints found")
        
        # Try to add unique constraint on (apartment_listings_id, DATE(time))
        # Note: MySQL doesn't support functional indexes in older versions, 
        # so we'll use a composite key approach
        
        print("\nAdding unique constraint (apartment_listings_id, date)...")
        
        try:
            # First, check if there's a date column
            cursor.execute("SHOW COLUMNS FROM apartment_listings_price_changes")
            columns = [col[0] for col in cursor.fetchall()]
            print(f"Current columns: {columns}")
            
            if 'date' not in columns:
                print("Adding 'date' column (DATE type) to store just the date part...")
                cursor.execute("""
                    ALTER TABLE apartment_listings_price_changes 
                    ADD COLUMN date DATE GENERATED ALWAYS AS (DATE(time)) STORED
                """)
                print("✓ Added 'date' column")
            
            # Now add the unique constraint
            print("Adding unique constraint on (apartment_listings_id, date)...")
            cursor.execute("""
                ALTER TABLE apartment_listings_price_changes 
                ADD UNIQUE KEY unique_apartment_date (apartment_listings_id, date)
            """)
            print("✓ Added unique constraint")
            
            conn.commit()
            print("\n✓ Changes committed successfully")
            print("Future duplicate entries will be prevented by database constraint")
            
        except mysql.connector.Error as e:
            if "Duplicate entry" in str(e):
                print(f"\n⚠️ Could not add constraint - duplicates still exist: {e}")
                print("Run delete_price_change_duplicates.py first")
            elif "Duplicate key name" in str(e):
                print(f"\n✓ Constraint already exists: {e}")
            else:
                print(f"\n✗ Error adding constraint: {e}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    add_unique_constraint()
