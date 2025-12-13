import mysql.connector

# Check remote for 911 tables
conn = mysql.connector.connect(
    host='172.104.206.182', 
    port=3306, 
    user='seattlelisted_usr', 
    password='T@5z6^pl}', 
    database='offta', 
    connection_timeout=30
)
cursor = conn.cursor()

# Check all tables with 911 in name
cursor.execute("SHOW TABLES LIKE '%911%'")
tables = cursor.fetchall()
print("Tables matching 911:", [t[0] for t in tables])

# Show all tables
cursor.execute("SHOW TABLES")
all_tables = cursor.fetchall()
print(f"\nTotal tables on remote: {len(all_tables)}")
print("All tables:", sorted([t[0] for t in all_tables]))

cursor.close()
conn.close()
