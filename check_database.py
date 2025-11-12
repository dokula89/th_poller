#!/usr/bin/env python3
"""
Check if networks table has data and stats columns exist
"""

import mysql.connector
from config_auth import DB_CONFIG

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor(dictionary=True)
    
    # Check if error_message column exists
    cursor.execute("SHOW COLUMNS FROM networks LIKE 'error_message'")
    if cursor.fetchone():
        print("✓ error_message column exists in networks table")
    else:
        print("✗ error_message column NOT found - run add_error_message_column.py")
    
    # Check for network_daily_stats table
    cursor.execute("SHOW TABLES LIKE 'network_daily_stats'")
    if cursor.fetchone():
        print("✓ network_daily_stats table exists")
        
        # Check stats data
        cursor.execute("SELECT COUNT(*) as cnt FROM network_daily_stats")
        result = cursor.fetchone()
        print(f"  {result['cnt']} stats records found")
        
        # Show sample
        cursor.execute("SELECT * FROM network_daily_stats LIMIT 3")
        for row in cursor.fetchall():
            print(f"  Network {row.get('source_id')}: Δ${row.get('price_changes')}, +{row.get('apartments_added')}, -{row.get('apartments_subtracted')}, Total:{row.get('total_listings')}")
    else:
        print("✗ network_daily_stats table NOT found - needs to be created")
    
    # Check networks table data
    cursor.execute("SELECT id, link, status, error_message FROM networks LIMIT 5")
    rows = cursor.fetchall()
    print(f"\n✓ {len(rows)} networks found in database:")
    for row in rows:
        error_msg = row.get('error_message', '')
        error_display = f" | Error: {error_msg[:40]}..." if error_msg else ""
        print(f"  ID {row['id']}: {row['link'][:50]} | Status: {row['status']}{error_display}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"✗ Database error: {e}")
