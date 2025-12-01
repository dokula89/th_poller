# Parcel Tab Fix - Summary

## Changes Made

### ✅ Fixed Parcel Tab Query
**Before:** Showed addresses that ALREADY HAVE parcel data
- Query: `INNER JOIN google_addresses ga ON ga.king_county_parcels_id = kcp.id`
- This showed `king_county_parcels` records that were linked to `google_addresses`

**After:** Shows addresses that DON'T HAVE parcel data yet
- Query: `WHERE ga.king_county_parcels_id IS NULL`
- This shows `google_addresses` records that need parcel processing

### ✅ Added Statistics
When Parcel tab is active, the status label now shows:
```
📊 X addresses without parcel data | Y with parcel data | Z total
```

Example: `📊 1,234 addresses without parcel data | 567 with parcel data | 1,801 total`

## What You'll See Now

### Parcel Tab (Extractor → Parcel)
- **ID Column**: google_addresses.id (not king_county_parcels.id)
- **Address Column**: Full address from google_addresses
- **Metro Column**: Metro name (Seattle, Bellevue, etc.)
- **Data Column**: Empty "{}" because these addresses don't have parcel data yet
- **✏️ Column**: Edit button to launch parcel automation

### Status Label
Shows real-time statistics for the selected metro:
- How many addresses still need parcel data
- How many addresses already have parcel data
- Total address count

## How It Works

1. **User clicks Extractor button**
2. **User clicks Parcel tab**
3. **Query runs**: Finds all `google_addresses` WHERE `king_county_parcels_id IS NULL`
4. **Statistics displayed**: Count of addresses with/without parcel data
5. **Table shows**: Addresses that need processing (no parcel data yet)

## Next Steps

When you click the **View** or **✏️** button for an address:
1. Parcel automation window opens
2. You can capture the parcel popup
3. Image saved as `parcels_{google_addresses_id}.png`
4. Run `python process_with_openai.py` to process batch
5. Database updates:
   - Inserts into `king_county_parcels`
   - Updates `google_addresses.king_county_parcels_id`
   - Updates `king_county_parcels.google_addresses_id`
6. Address disappears from Parcel tab (now has data!)

## Testing

To test the fix:
1. Run `python config_hud.py`
2. Click **Extractor** button
3. Click **Parcel** tab
4. You should see addresses WITHOUT parcel data
5. Status label should show statistics
6. Data column should show "{}" (empty, not actual parcel data)
