import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1',
    user='local_uzr',
    password='fuck',
    database='offta'
)
cursor = conn.cursor()

# Check table structure
print("network_daily_stats table structure:")
cursor.execute("SHOW CREATE TABLE network_daily_stats")
result = cursor.fetchone()
print(result[1])

print("\n" + "="*80 + "\n")

# Check indexes
print("Indexes on network_daily_stats:")
cursor.execute("SHOW INDEX FROM network_daily_stats")
for idx in cursor.fetchall():
    print(f"  {idx}")

conn.close()
