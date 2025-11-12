import mysql.connector as mysql

def reset_running_jobs():
    conn = mysql.connect(
        host='172.104.206.182',
        port=3306,
        user='seattlelisted_usr',
        password='T@5z6^pl}',
        database='offta'
    )
    
    cur = conn.cursor()
    cur.execute('UPDATE queue_websites SET status="queued" WHERE status="running"')
    conn.commit()
    count = cur.rowcount
    cur.close()
    conn.close()
    return count

if __name__ == "__main__":
    count = reset_running_jobs()
    print(f"Reset {count} running jobs to queued status")