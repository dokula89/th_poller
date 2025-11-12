# Step5 Database Setup

## Issue
The Queue Poller app was showing repeated errors:
```
[Queue] Stats fetch failed: 1049 (42000): Unknown database 'step5'
```

This is because the `step5` database doesn't exist yet, but the app tries to fetch statistics from it for the Networks tab.

## Solution

### Option 1: Run the setup script (Recommended)
```powershell
.\setup_step5_database.ps1
```

This will automatically create the `step5` database and `apartment_changes` table.

### Option 2: Manual SQL execution
If the script doesn't work, run the SQL manually:

1. Open MySQL Workbench or command line
2. Execute the contents of `create_step5_database.sql`

### Option 3: Continue without the database
The app will now work fine even without the `step5` database! The statistics columns (Δ$, +, -) will just show zeros until you create the database.

## What This Database Does

The `step5` database tracks apartment listing changes:

- **Price Changes** (Δ$ column): Tracks when listing prices change
- **New Listings** (+ column): Tracks when new apartments are added
- **Removed Listings** (- column): Tracks when apartments are removed

### Database Schema

**Database:** `step5`
**Table:** `apartment_changes`

| Column | Type | Description |
|--------|------|-------------|
| id | INT | Auto-increment primary key |
| source_id | VARCHAR(50) | Network/source ID from queue_websites |
| change_type | ENUM | 'price_change', 'apartment_added', or 'apartment_subtracted' |
| changed_at | DATETIME | When the change occurred |

## Testing

After creating the database:

1. Open the Queue Poller app
2. Click the "Networks" tab
3. The Δ$, +, - columns should now show statistics (once data is tracked)
4. No more error messages in the debug log!

## Notes

- The app will continue to work without this database, but statistics will show as 0
- The database is created once and used by all network tracking operations
- Stats are populated when Step 5 (Insert DB) runs and detects changes
