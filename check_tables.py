import mysql.connector
conn = mysql.connector.connect(
    host='172.104.206.182',
    user='seattlelisted_usr',
    password='T@5z6^pl}',
    database='offta'
)
cursor = conn.cursor()
cursor.execute("SHOW TABLES LIKE '%openai%'")
tables = cursor.fetchall()
print(f'OpenAI related tables: {tables}')
cursor.execute("SHOW TABLES LIKE '%cost%'")
tables = cursor.fetchall()
print(f'Cost related tables: {tables}')
cursor.close()
conn.close()
