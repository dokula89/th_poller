import mysql.connector

conn = mysql.connector.connect(
    host='127.0.0.1',
    user='local_uzr',
    password='fuck',
    database='offta'
)
cursor = conn.cursor()

cursor.execute("SHOW TABLES LIKE 'network%'")
tables = cursor.fetchall()
print("Tables starting with 'network':")
for table in tables:
    print(f"  - {table[0]}")

# Check if 'networks' table exists and show its columns
cursor.execute("SHOW TABLES LIKE 'networks'")
if cursor.fetchone():
    print("\n'networks' table columns:")
    cursor.execute("DESCRIBE networks")
    for col in cursor.fetchall():
        print(f"  - {col[0]} ({col[1]})")
else:
    print("\n'networks' table does NOT exist")

conn.close()
