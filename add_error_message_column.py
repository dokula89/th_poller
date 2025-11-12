"""
Add error_message column to networks table
"""
import mysql.connector

try:
    conn = mysql.connector.connect(
        host="127.0.0.1",
        user="local_uzr",
        password="fuck",
        database="offta"
    )
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("SHOW COLUMNS FROM networks LIKE 'error_message'")
    result = cursor.fetchone()
    
    if not result:
        print("Adding error_message column to networks table...")
        cursor.execute("ALTER TABLE networks ADD COLUMN error_message TEXT NULL")
        conn.commit()
        print("✅ Column added successfully!")
    else:
        print("✅ error_message column already exists")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Error: {e}")
