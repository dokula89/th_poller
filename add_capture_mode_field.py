"""
Add capture_mode field to queue_websites table
Allows choosing between 'headless' (automated HTTP request) or 'browser' (manual browser automation)
"""

import mysql.connector

try:
    # Connect to database
    conn = mysql.connector.connect(
        host='localhost',
        port=3306,
        user='root',
        password='',
        database='offta'
    )
    cursor = conn.cursor()
    
    # Add capture_mode column to queue_websites
    print("Adding capture_mode column to queue_websites table...")
    cursor.execute("""
        ALTER TABLE queue_websites 
        ADD COLUMN capture_mode ENUM('headless', 'browser') DEFAULT 'headless'
        AFTER the_css
    """)
    print("✓ Added capture_mode to queue_websites")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print("\n✅ Database migration completed successfully!")
    print("\nField details:")
    print("  - Column: capture_mode")
    print("  - Type: ENUM('headless', 'browser')")
    print("  - Default: 'headless'")
    print("  - Location: After 'the_css' column")
    
except mysql.connector.Error as err:
    if err.errno == 1060:
        print("⚠️  Column 'capture_mode' already exists - skipping")
    else:
        print(f"❌ Error: {err}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
