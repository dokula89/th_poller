# Database Sync Feature

## Overview
A new "🔄 Sync DB" button has been added to the queue poller HUD that allows you to synchronize local database tables to the remote production server.

## Location
The button is located in the top action bar of the queue poller, after the "Extractor" button.

## Tables Synced
When you click the Sync DB button, the following tables will be exported from your local database and uploaded to replace the tables on the remote server:

- `queue_websites` - Queue management and job tracking
- `networks` - Network configurations and results
- `apartment_listings` - Extracted apartment listings data
- `apartment_listings_price_changes` - Price change history tracking
- `google_addresses` - Geocoded address data
- `google_places` - Google Places API results
- `network_daily_stats` - Daily statistics tracking

## How It Works

1. **Click Button**: Click the "🔄 Sync DB" button in the top action bar

2. **Database Comparison**: The system automatically:
   - Connects to both local and remote databases
   - Counts rows in each table
   - Calculates the differences (how many rows will be added/removed)

3. **Review Window**: A detailed comparison window appears showing:
   - Table names
   - Local row count
   - Remote row count
   - Difference (e.g., "+150 rows" or "-25 rows")
   - Total summary across all tables
   - Warning about data replacement

4. **Confirmation**: Review the changes and click:
   - "✓ Proceed with Sync" to continue
   - "✗ Cancel" to abort the operation

5. **Export**: The system uses `mysqldump` to export the selected tables from your local database (localhost)

6. **Upload**: The exported SQL file is imported to the remote server (172.104.206.182:23655) using the MySQL client

7. **Completion**: A success message shows which tables were synced, or an error message if something went wrong

8. **Cleanup**: Temporary SQL files are automatically deleted after the sync completes

## Requirements

- **mysqldump**: Must be available in your system PATH (comes with MySQL installation)
- **mysql client**: Must be available in your system PATH
- **Network Access**: Must be able to connect to 172.104.206.182:23655
- **Remote Credentials**: Uses daniel/Driver89* (hardcoded in the script)

## Activity Log

All sync operations are logged to the activity log with the `[Sync]` prefix:
- `[Sync] Starting database sync...`
- `[Sync] Dumping X tables...`
- `[Sync] ✓ Tables dumped successfully`
- `[Sync] Uploading to remote server...`
- `[Sync] ✓ Sync completed successfully!`

Or in case of errors:
- `[Sync] ✗ Sync failed: [error message]`

## Important Notes

⚠️ **WARNING**: This operation will **REPLACE** all data in the remote tables with data from your local database. Make sure your local data is correct before syncing!

- Sync operations are logged to the main log file for debugging
- Temporary files are created in your system's temp directory and cleaned up automatically
- The operation uses `--single-transaction` and `--lock-tables=false` to minimize disruption
- Large tables may take several seconds to sync

## Troubleshooting

**"mysqldump failed"**: Ensure MySQL tools are installed and in your PATH
**"mysql import failed"**: Check network connectivity to 172.104.206.182:23655
**Connection refused**: Verify the remote MySQL server is running and accessible
**Permission denied**: Verify credentials (daniel/Driver89*) are correct

## Technical Details

- **Local DB**: localhost:3306, user: root (no password), database: offta
- **Remote DB**: 172.104.206.182:23655, user: daniel, password: Driver89*, database: offta
- **Method**: Direct MySQL dump and restore (no SFTP involved)
- **Transaction Safety**: Uses single-transaction mode to ensure consistency
