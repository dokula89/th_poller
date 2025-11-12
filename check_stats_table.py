import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1',
    user='local_uzr',
    password='fuck',
    database='offta'
)
cursor = conn.cursor()

# Check if table exists
cursor.execute("SHOW TABLES LIKE 'network_daily_stats'")
table_exists = cursor.fetchone()
print(f"Table exists: {table_exists is not None}")

if table_exists:
    # Get total rows
    cursor.execute("SELECT COUNT(*) FROM network_daily_stats")
    total = cursor.fetchone()[0]
    print(f"Total rows: {total}")
    
    # Get today's rows
    cursor.execute("SELECT COUNT(*) FROM network_daily_stats WHERE date = '2025-11-05'")
    today = cursor.fetchone()[0]
    print(f"Today's rows (2025-11-05): {today}")
    
    # Show sample data
    cursor.execute("SELECT * FROM network_daily_stats ORDER BY date DESC LIMIT 5")
    rows = cursor.fetchall()
    print(f"\nLast 5 rows:")
    for row in rows:
        print(f"  {row}")
    
    # Check for networks 2, 4, 7 specifically
    cursor.execute("SELECT network_id, date, price_changes, apartments_added, apartments_subtracted FROM network_daily_stats WHERE network_id IN (2, 4, 7) ORDER BY date DESC LIMIT 10")
    network_rows = cursor.fetchall()
    print(f"\nRows for networks 2, 4, 7 (marked as 'done'):")
    for row in network_rows:
        print(f"  {row}")

conn.close()
