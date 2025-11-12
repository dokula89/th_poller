# Queue Table API Information

## API Endpoint (Primary Method)

**Base URL**: `https://api.trustyhousing.com/manual_upload/queue_website_api.php`

### Parameters:
- `table` - Table name (queue_websites, listing_networks, parcel, code, 911)
- `status` - Status filter (queued, running, done, error)
- `limit` - Max records to return (default: 100)

### Example Requests:

**Get queued items from queue_websites:**
```
https://api.trustyhousing.com/manual_upload/queue_website_api.php?table=queue_websites&status=queued&limit=100
```

**Get ALL items from a table (for counting by status):**
```
https://api.trustyhousing.com/manual_upload/queue_website_api.php?table=queue_websites&limit=1000
```

**Get running items from listing_networks:**
```
https://api.trustyhousing.com/manual_upload/queue_website_api.php?table=listing_networks&status=running&limit=100
```

### Expected Response Format:

**Success Response:**
```json
{
  "ok": true,
  "data": [
    {
      "id": 123,
      "link": "https://example.com",
      "status": "queued",
      "priority": 5,
      "attempts": 0,
      "updated_at": "2025-10-30 12:34:56",
      "created_at": "2025-10-30 12:00:00"
    }
  ],
  "meta": {
    "total": 6,
    "limit": 50,
    "offset": 0,
    "count": 6
  }
}
```

**Error response:**
```json
{
  "ok": false,
  "error": "Error message here"
}
```

## Status Counting

The UI counts status by:
1. Fetching ALL records from the table (no status filter)
2. Iterating through each record
3. Counting based on the `status` field value
4. Displaying counts in the chips (Queued/Running/Done/Error)

This happens automatically every 5 seconds when auto-refresh is enabled.

## Direct Database Connection (For Updates Only)
- **Host**: 172.104.206.182
- **Port**: 3306
- **Database**: offta
- **User**: seattlelisted_usr

## SQL Queries Used

### For `queue_websites` Table:
```sql
SELECT id, link, priority, attempts, updated_at, 
       the_css, source_table, source_id, created_at
FROM `queue_websites`
WHERE status = 'queued'  -- or 'running', 'done', 'error'
ORDER BY priority DESC, id ASC
LIMIT 100
```

### For Other Tables (listing_networks, parcel, code, 911):
```sql
SELECT id, 
       COALESCE(link, name, details, '') as link, 
       COALESCE(priority, 0) as priority,
       COALESCE(attempts, 0) as attempts,
       updated_at
FROM `[table_name]`
WHERE status = 'queued'  -- or 'running', 'done', 'error'
ORDER BY id DESC
LIMIT 100
```

## Status Values
- **queued** - Jobs waiting to be processed
- **running** - Jobs currently being processed
- **done** - Jobs completed successfully
- **error** - Jobs that failed

## Direct MySQL Test Commands

### Test connection:
```powershell
# Using mysql command line client
mysql -h 172.104.206.182 -P 3306 -u seattlelisted_usr -p offta
# Password: T@5z6^pl}
```

### Check queued items:
```sql
SELECT COUNT(*) as total FROM queue_websites WHERE status = 'queued';
SELECT * FROM queue_websites WHERE status = 'queued' ORDER BY priority DESC, id ASC LIMIT 10;
```

### Check all status counts:
```sql
SELECT status, COUNT(*) as count 
FROM queue_websites 
GROUP BY status;
```

## Python Direct Query Example

```python
import mysql.connector

conn = mysql.connector.connect(
    host="172.104.206.182",
    port=3306,
    user="seattlelisted_usr",
    password="T@5z6^pl}",
    database="offta",
    connect_timeout=10
)

cursor = conn.cursor(dictionary=True)
cursor.execute("SELECT * FROM queue_websites WHERE status = %s LIMIT 10", ("queued",))
rows = cursor.fetchall()

for row in rows:
    print(f"ID: {row['id']}, Link: {row['link']}, Priority: {row['priority']}")

cursor.close()
conn.close()
```

## Troubleshooting

If the table shows "Loading..." and crashes:
1. Check `debug_queue.log` for the exact error
2. Verify database is reachable: `Test-NetConnection -ComputerName 172.104.206.182 -Port 3306`
3. Check if there are any queued records in the database
4. Verify the table schema matches the query (columns exist)

## Log File Location
All debug output is written to: `c:\Users\dokul\Desktop\robot\th_poller\debug_queue.log`
