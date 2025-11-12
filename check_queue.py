#!/usr/bin/env python3
import mysql.connector as mysql

conn = mysql.connect(
    host='172.104.206.182',
    port=3306,
    user='seattlelisted_usr',
    password='T@5z6^pl}',
    database='offta'
)

try:
    cur = conn.cursor(dictionary=True)
    # Check current queue status
    cur.execute('SELECT status, COUNT(*) as count FROM queue_websites GROUP BY status')
    status = cur.fetchall()
    
    print("\nQueue status:")
    for s in status:
        print(f"{s['status']}: {s['count']}")
        
    # Check running jobs in detail
    cur.execute('SELECT id, link, status, attempts, updated_at FROM queue_websites WHERE status="running"')
    running = cur.fetchall()
    
    if running:
        print("\nRunning jobs:")
        for job in running:
            print(f"ID {job['id']}: {job['link']} (attempts: {job['attempts']}, last update: {job['updated_at']})")
    else:
        print("\nNo running jobs found")
        
    # Show queued jobs
    cur.execute('SELECT id, link FROM queue_websites WHERE status="queued" ORDER BY priority DESC, id ASC LIMIT 20')
    queued = cur.fetchall()
    
    if queued:
        print("\nQueued jobs (auto steps marked ✓):")
        # Define steps and whether they're automatic in current pipeline
        steps = [
            ("Capture", True),
            ("Extract", True),
            ("ImagesDL", True),
            ("SFTP JSON", True),
            ("SFTP IMG", True),
            ("PublicCheck", False),
        ]

        # Prepare header
        headers = ["ID", "Link"] + [name for name, _ in steps]
        # Column widths
        id_w = 5
        link_w = 60
        col_w = 11
        # Print header row
        def pad(s, w):
            s = str(s)
            return s[:w] + ("" if len(s) >= w else " " * (w - len(s)))

        header_line = pad(headers[0], id_w) + "  " + pad(headers[1], link_w) + "  " + "  ".join(pad(h, col_w) for h in headers[2:])
        print(header_line)
        print("-" * len(header_line))

        # Build rows
        for job in queued:
            jid = pad(job.get('id', ''), id_w)
            link = str(job.get('link', '') or '')
            link = pad(link, link_w)
            marks = ["✓" if auto else "" for _, auto in steps]
            row = jid + "  " + link + "  " + "  ".join(pad(m, col_w) for m in marks)
            print(row)
    else:
        print("\nNo queued jobs found")

except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()