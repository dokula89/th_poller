import mysql.connector as mysql
from datetime import datetime, timedelta

print("Checking running jobs status...")

# Connect directly to MySQL
db_config = {
    "host": "172.104.206.182",
    "port": 3306,
    "user": "seattlelisted_usr",
    "password": "T@5z6^pl}",
    "database": "offta",
}

try:
    conn = mysql.connect(**db_config)
    print("Connected to MySQL successfully")
    cur = conn.cursor(dictionary=True)

try:
    # Get running jobs
    cur.execute('SELECT id, status, updated_at FROM queue_websites WHERE status="running"')
    running = cur.fetchall()
    print("\nCurrently running jobs:")
    for job in running:
        print(f"ID: {job['id']}, Last updated: {job['updated_at']}")
    
    # Reset stale running jobs to queued
    time_threshold = datetime.now() - timedelta(minutes=5)
    cur.execute(
        'UPDATE queue_websites SET status="queued", updated_at=NOW() WHERE status="running" AND updated_at < %s',
        (time_threshold,)
    )
    conn.commit()
    if cur.rowcount > 0:
        print(f"\nReset {cur.rowcount} stale running jobs to queued status")

finally:
    cur.close()
    conn.close()