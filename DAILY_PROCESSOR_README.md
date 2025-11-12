# Daily Capture Processor

Automatically processes HTML files from today's Captures folder, uses ChatGPT to extract apartment listings, downloads images, and updates the database.

## Features

- ✅ Auto-detects today's capture folder (e.g., `Captures/2025-10-22/`)
- ✅ Processes all `.html` files in the folder
- ✅ Uses ChatGPT (GPT-4) to extract structured listing data
- ✅ Extracts unique IDs from listing URLs
- ✅ Downloads and saves images to `Captures/images/`
- ✅ Upserts to `apartment_listings` MySQL table (insert new, update existing)
- ✅ Creates JSON backup of extracted data
- ✅ Detailed console output with progress

## Setup

### 1. Install Dependencies

```powershell
pip install openai requests mysql-connector-python
```

### 2. Set OpenAI API Key

```powershell
# Permanent (recommended)
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-your-key-here', 'User')

# Or temporary (current session only)
$env:OPENAI_API_KEY = "sk-your-key-here"
```

Get your API key from: https://platform.openai.com/api-keys

### 3. Verify MySQL Config

Ensure `config_utils.py` has correct MySQL credentials:
- `MYSQL_HOST`
- `MYSQL_PORT`
- `MYSQL_USER`
- `MYSQL_PASSWORD`
- `MYSQL_DB`

## Usage

### Run Manually

```powershell
cd C:\Users\dokul\Desktop\robot\th_poller
python process_daily_captures.py
```

### Schedule Daily (Windows Task Scheduler)

1. Open Task Scheduler
2. Create Task:
   - **Name**: Process Daily Apartment Captures
   - **Trigger**: Daily at specific time (e.g., 11:00 PM)
   - **Action**: Start a program
     - **Program**: `python`
     - **Arguments**: `C:\Users\dokul\Desktop\robot\th_poller\process_daily_captures.py`
     - **Start in**: `C:\Users\dokul\Desktop\robot\th_poller`
3. Save and test

### Automate with PowerShell Script

Create `run_daily_processor.ps1`:
```powershell
cd C:\Users\dokul\Desktop\robot\th_poller
python process_daily_captures.py
if ($LASTEXITCODE -eq 0) {
    Write-Host "Success!" -ForegroundColor Green
} else {
    Write-Host "Failed!" -ForegroundColor Red
}
```

## How It Works

### 1. Folder Detection
- Looks for `Captures/YYYY-MM-DD/` folder matching today's date
- Scans for all `.html` files

### 2. AI Extraction
- Sends HTML content to ChatGPT (GPT-4o-mini)
- AI extracts:
  - Title, address, price, bedrooms, bathrooms, sqft
  - Images, contact info, descriptions
  - Application links
- Returns structured JSON data

### 3. Unique ID Extraction
Tries multiple patterns to extract unique IDs from listing URLs:
- UUID format: `ba786613-8954-447d-8b6c-c5942b3c218b`
- Numeric IDs: `12345`
- Path segments: `/detail/apartment-name`
- Fallback: MD5 hash of URL

### 4. Image Download
- Downloads images from extracted URLs
- Saves to `Captures/images/` with unique filenames
- Format: `{listing_id}_{hash}.jpg`
- Skips already-downloaded images

### 5. Database Upsert
- Checks if listing exists by ID
- **Update**: If ID exists, updates all fields
- **Insert**: If new, inserts as new record
- Sets `time_created` and `time_updated` timestamps

### 6. JSON Backup
- Saves `extracted_listings.json` in the same folder
- Contains all extracted data for review/debugging

## Output Example

```
============================================================
Daily Capture Processor
============================================================

📁 Processing folder: C:\Users\dokul\Desktop\robot\th_poller\Captures\2025-10-22
Found 1 HTML file(s)

📄 Processing: networks_1.html
  📍 Source URL: https://example.com/listings
  → Sending HTML to ChatGPT for analysis...
  ✓ Extracted 12 listings from HTML
  ✓ Downloaded image: ba786613_a1b2c3d4.jpg
  ✓ Listing 1: Spacious 1BR Apartment - ID: ba786613-8954-447d
  ✓ Listing 2: Modern Studio Downtown - ID: f9e8d7c6-5432-1a2b
  ...

💾 Saved backup: extracted_listings.json

💾 Upserting 12 listings to database...
  ✓ Inserted: Spacious 1BR Apartment (ID: ba786613-8954-447d)
  ↻ Updated: Modern Studio Downtown (ID: f9e8d7c6-5432-1a2b)
  ...

✅ Database updated: 10 inserted, 2 updated

============================================================
✅ Processing complete: 12 listings processed
============================================================
```

## Error Handling

- **No API key**: Aborts with clear error message
- **No HTML files**: Exits gracefully with warning
- **AI extraction fails**: Logs error, continues with other files
- **Database error**: Shows detailed MySQL error with traceback
- **Image download fails**: Logs warning, continues without image

## Cost Estimation

Using `gpt-4o-mini` model:
- Rate: ~$0.15 per 1M tokens
- Typical HTML file: ~5,000 tokens
- Cost per file: ~$0.001 (less than 1 cent)
- **Daily cost**: < $0.01 for typical usage

## Troubleshooting

### "OPENAI_API_KEY environment variable not set"
```powershell
$env:OPENAI_API_KEY = "sk-your-key-here"
```

### "No captures folder found for today"
- Check folder exists: `Captures/YYYY-MM-DD/`
- Verify date format matches exactly

### "Database error"
- Verify MySQL is running
- Check credentials in `config_utils.py`
- Ensure `apartment_listings` table exists

### "Import error"
```powershell
pip install openai requests mysql-connector-python
```

## Files Created

- `Captures/YYYY-MM-DD/extracted_listings.json` - JSON backup
- `Captures/images/*.jpg` - Downloaded listing images
- Database records in `apartment_listings` table

## Integration with Existing Workflow

This script complements the Map Editor:
1. **Poller** saves HTML to `Captures/YYYY-MM-DD/`
2. **This script** extracts listings and updates database
3. **Map Editor** can still be used for custom field mapping if needed

## Next Steps

- Run the script to test
- Schedule it to run daily
- Monitor the output and database
- Adjust AI prompts if needed for better extraction
