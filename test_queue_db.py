#!/usr/bin/env python3
"""Quick test to verify database connection and queue tables"""
import mysql.connector

DB_CONFIG = {
    'host': '172.104.206.182',
    'port': 3306,
    'user': 'seattlelisted_usr',
    'password': 'T@5z6^pl}',
    'database': 'offta'
}

print("Testing database connection...")
try:
    conn = mysql.connector.connect(**DB_CONFIG, connect_timeout=10)
    print("✓ Connected to database")
    
    cur = conn.cursor(dictionary=True)
    
    # Test queue_websites table
    print("\n--- Testing queue_websites ---")
    cur.execute("SELECT COUNT(*) as total FROM queue_websites")
    total = cur.fetchone()
    print(f"Total records: {total['total']}")
    
    # Use parameterized query (safe way)
    cur.execute("SELECT status, COUNT(*) as count FROM queue_websites GROUP BY status")
    for row in cur.fetchall():
        print(f"  {row['status']}: {row['count']}")
    
    # Get sample queued record with parameterized query
    status_to_check = 'queued'
    cur.execute("""
        SELECT id, link, priority, attempts, updated_at, status
        FROM queue_websites 
        WHERE status=%s
        LIMIT 5
    """, (status_to_check,))
    
    samples = cur.fetchall()
    print(f"\nFound {len(samples)} queued records:")
    for i, sample in enumerate(samples, 1):
        print(f"\n  Record {i}:")
        print(f"    ID: {sample['id']}")
        print(f"    Link: {sample['link'][:50] if sample['link'] else 'None'}...")
        print(f"    Priority: {sample['priority']}")
        print(f"    Attempts: {sample['attempts']}")
        print(f"    Updated: {sample['updated_at']}")
    
    if not samples:
        print("  (No queued records found)")
    
    cur.close()
    conn.close()
    print("\n✓ Database test complete")
    
except Exception as e:
    print(f"✗ Database error: {e}")
    import traceback
    traceback.print_exc()

input("\nPress Enter to exit...")

