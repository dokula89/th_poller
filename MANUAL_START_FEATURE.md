# Manual Step-by-Step Job Control

## Overview
The queue table now shows a **5-step workflow** with individual Start buttons for each step. You can run steps one at a time or enable Auto Run to process entire jobs automatically.

## 5-Step Workflow

### Step 1: Capture HTML (1.HTML)
- **Action**: Downloads the HTML from the URL
- **Output**: Saves HTML to `Captures/{date}/job_{id}.html`
- **Click**: "▶ Start" button in the "1.HTML" column

### Step 2: Create JSON (2.JSON)
- **Action**: Calls `http://localhost/process_html_with_openai.php` to extract structured data using AI
- **Input**: Requires Step 1 to be completed
- **Parameters**: `file`, `model=gpt-4o-mini`, `method=local`, `process=1`
- **Output**: Saves JSON to `Captures/{date}/job_{id}.json`
- **Click**: "▶ Start" button in the "2.JSON" column

### Step 3: Manual Match (3.Match)
- **Action**: Calls `https://172.104.206.182/manual_match.php` which extracts images, uploads them, and matches data
- **Input**: Requires Steps 1 and 2 to be completed
- **Output**: Images extracted, uploaded to server, and data matched
- **Click**: "▶ Start" button in the "3.Match" column
- **Note**: This step combines image extraction and upload in one operation

### Step 4: Process DB (4.DB)
- **Action**: Inserts listing data into the database
- **Input**: Requires Step 2 to be completed
- **Output**: Creates entry in `apartment_listings` table, returns listing ID
- **Click**: "▶ Start" button in the "4.DB" column

### Step 5: Rename Images (5.Rename)
- **Action**: Renames image files to match the apartment_listings ID
- **Input**: Requires Step 4 to be completed
- **Output**: Images renamed with listing ID prefix
- **Click**: "▶ Start" button in the "5.Rename" column

## Table Columns

| Column | Description |
|--------|-------------|
| ID | Job ID from the queue |
| Link | First 30 characters of the URL |
| 1.HTML | Capture HTML step - click to start |
| 2.JSON | Create JSON step - click to start |
| 3.Match | Manual match (images + upload) - click to start |
| 4.DB | Process and insert into DB - click to start |
| 5.Rename | Rename images - click to start |

## Step Status Indicators

- **▶ Start** - Step not started, click to begin
- **⏳** - Step currently running
- **✓** - Step completed successfully
- **✗** - Step failed with error

## Auto Run Checkbox

### Manual Mode (Unchecked - Default)
- Steps only run when you click their Start buttons
- You control the exact sequence and timing
- Perfect for testing or selective processing

### Auto Run Mode (Checked)
- All 6 steps run automatically in sequence
- Worker processes complete jobs from start to finish
- Traditional automated behavior

## How to Use

### Manual Step-by-Step Processing
1. Open the queue table (click "Queue" button)
2. Leave "Auto Run" **unchecked**
3. Find a queued job
4. Click "▶ Start" in the "1.HTML" column
5. Wait for "✓" to appear
6. Click "▶ Start" in the "2.JSON" column
7. Wait for "✓" to appear
8. Click "▶ Start" in the "3.Match" column (handles images + upload)
9. Continue through steps 4-5

### Automated Processing
1. Check the "Auto Run" checkbox
2. Worker automatically processes all steps for queued jobs
3. Monitor progress via status indicators

## API Endpoints Used

### Step 1: Capture HTML
- Direct HTTP GET request to the source URL
- Saves HTML to local file system

### Step 2: Create JSON with OpenAI
- **Endpoint**: `http://localhost/process_html_with_openai.php`
- **Method**: GET
- **Parameters**: 
  - `file`: URL-encoded path to HTML file
  - `model`: `gpt-4o-mini`
  - `method`: `local`
  - `process`: `1`
- **Example**: `http://localhost/process_html_with_openai.php?file=C%3A%5CUsers%5Cdokul%5CDesktop%5Crobot%5Cth_poller%5CCaptures%5C2025-10-29%5Cnetworks_1.html&model=gpt-4o-mini&method=local&process=1`

### Step 3: Manual Match
- **Endpoint**: `https://172.104.206.182/manual_match.php`
- **Method**: POST
- **Payload**: `{job_id, data, html_file, source_url}`
- **Function**: Extracts images, uploads to server, matches data

### Step 4: Process DB
- **Endpoint**: `insert_listing.php`
- **Method**: POST
- **Payload**: `{data, job_id}`

### Step 5: Rename Images
- **Endpoint**: `rename_images.php`
- **Method**: POST
- **Payload**: `{job_id}`

## Step Status Tracking
- **Endpoint**: `queue_step_api.php`
- **Method**: POST
- **Payload**: `{table, id, step, status, message, timestamp}`

## Files Modified
- `config_utils.py`: Complete workflow implementation
  - Table columns updated to show 6 steps
  - Click handler detects which step column was clicked
  - `_start_job_step()` - Initiates step execution
  - `_execute_step()` - Runs the actual step logic
  - `_step_capture_html()` through `_step_rename_images()` - Individual step implementations
  - `_update_step_status()` - Updates step status via API

## Technical Details

### Step Data Storage
Steps are tracked in a `steps` JSON field in the database:
```json
{
  "capture_html": "done",
  "create_json": "running",
  "manual_match": "pending",
  "process_db": "pending",
  "rename_images": "pending"
}
```

### Error Handling
- Each step has try/catch error handling
- Failed steps show "✗" and error message
- Can retry failed steps by clicking Start again
- Errors logged to `debug_queue.log`

### Dependencies
- Step 2 requires Step 1 (needs HTML file)
- Step 3 requires Steps 1 and 2 (needs HTML and JSON files)
- Step 4 requires Step 2 (needs JSON file)
- Step 5 requires Step 4 (needs listing ID)

## Testing Checklist
1. ✅ Verify 5 step columns appear in table
2. ✅ Click "▶ Start" in 1.HTML - should capture HTML
3. ✅ Verify "⏳" appears while running
4. ✅ Verify "✓" appears when complete
5. ✅ Click through all 5 steps in sequence
6. ✅ Check Auto Run - verify automatic processing
7. ✅ Uncheck Auto Run - verify manual mode
8. ✅ Test error handling - verify "✗" for failures

