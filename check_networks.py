import mysql.connector
conn = mysql.connector.connect(
    host='172.104.206.182',
    user='seattlelisted_usr',
    password='T@5z6^pl}',
    database='offta'
)
cursor = conn.cursor()
cursor.execute("SELECT id, link, source_table FROM queue_websites WHERE source_table = 'networks' ORDER BY id")
rows = cursor.fetchall()
print(f'Network entries: {len(rows)}')
for r in rows:
    print(f'  ID={r[0]}, {r[1][:50]}')
cursor.close()
conn.close()
