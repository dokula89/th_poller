#!/usr/bin/env python3
"""
Test script to randomly change 17 listing prices for network_id=1
Changes are +/- $200 from current price for testing price change detection
ONLY changes the price column - nothing else
"""

import mysql.connector
import random

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
    # Get 17 listings from network_id=1 that have prices
    print("Fetching 17 listings from network_id=1...")
    cursor.execute("""
        SELECT id, full_address, price 
        FROM apartment_listings 
        WHERE network_id = 1 AND price IS NOT NULL AND price > 0
        LIMIT 17
    """)
    
    listings = cursor.fetchall()
    
    if len(listings) < 17:
        print(f"⚠️ Warning: Only found {len(listings)} listings with prices for network_id=1")
    
    print(f"\nChanging prices for {len(listings)} listings:\n")
    
    changed_count = 0
    for listing_id, address, current_price in listings:
        # Random change between -$200 and +$200
        change = random.randint(-200, 200)
        new_price = max(100, current_price + change)  # Ensure price stays above $100
        
        # Update ONLY the price column (nothing else)
        cursor.execute("""
            UPDATE apartment_listings 
            SET price = %s
            WHERE id = %s
        """, (new_price, listing_id))
        
        change_symbol = "+" if change >= 0 else ""
        print(f"ID {listing_id:3d} | {address[:50]:50s} | ${current_price:5d} → ${new_price:5d} ({change_symbol}${change})")
        changed_count += 1
    
    # Commit changes
    conn.commit()
    
    print(f"\n✅ Successfully changed {changed_count} prices in the database!")
    print(f"📊 Now run Step 5 (Insert DB) to:")
    print(f"   - Detect these price changes")
    print(f"   - Log them to apartment_listings_price_changes table")
    print(f"   - Update other listing fields from JSON")
    print(f"   - Update time_updated timestamp via Step 5")

except Exception as e:
    print(f"❌ Error: {e}")
    conn.rollback()
finally:
    cursor.close()
    conn.close()
