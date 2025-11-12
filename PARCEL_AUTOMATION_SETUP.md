# Parcel Automation Setup Guide

## Overview
The Empty Parcels window now includes a **Start Parcel Capture** button that automates:
1. Opening the parcel website for your metro
2. Entering each address into the search field
3. Pressing Enter and waiting 4 seconds
4. Taking a screenshot
5. Using OCR to extract parcel data into JSON
6. Moving to the next address

## Prerequisites

### 1. Install Python Dependencies
```powershell
pip install -r requirements.txt
```

This will install:
- `selenium` - Browser automation
- `pyautogui` - GUI automation (backup)
- `pytesseract` - OCR engine wrapper
- `opencv-python` - Image processing
- `numpy` - Array operations for image processing

### 2. Install Tesseract OCR Engine

**Tesseract** is required for text extraction from screenshots.

#### Windows Installation:
1. Download the installer from: https://github.com/UB-Mannheim/tesseract/wiki
2. Run the installer (e.g., `tesseract-ocr-w64-setup-5.3.3.20231005.exe`)
3. Install to default location: `C:\Program Files\Tesseract-OCR\`
4. Add to PATH or set in Python:
   ```python
   pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
   ```

### 3. Install Chrome WebDriver

Selenium requires ChromeDriver to control Chrome.

#### Option A: Automatic (Recommended)
Selenium 4.x can auto-download ChromeDriver. Just ensure Chrome is installed.

#### Option B: Manual
1. Check your Chrome version: `chrome://version/`
2. Download matching ChromeDriver: https://chromedriver.chromium.org/downloads
3. Extract `chromedriver.exe` to a folder in PATH (or same folder as script)

## Usage

### 1. Open Empty Parcels Window
- In the Parcel tab, right-click on an "Empty Parcels" count
- Or click "Start" on a Parcel row to open both browser and window

### 2. Start Automation
- Click **▶ Start Parcel Capture** button
- The automation will:
  - Open Chrome to the parcel website
  - Process each address (20 per page)
  - Save screenshots and JSON to: `C:\Users\dokul\Desktop\robot\th_poller\Captures\parcels\`

### 3. Monitor Progress
- Status shows: `Processing 5/20: 123 Main St Seattle WA...`
- When complete: `✓ Completed 20/20 addresses`

### 4. Review Results
Output files in `Captures\parcels\`:
- **Screenshots**: `parcel_Seattle_12345_20251101_143022.png`
- **Individual JSON**: `parcel_Seattle_12345_20251101_143022.json`
- **Batch JSON**: `parcel_batch_Seattle_20251101_143530.json`

## JSON Output Format

### Individual Address JSON:
```json
{
  "id": 12345,
  "address": "123 Main St, Seattle, WA 98101",
  "screenshot": "C:\\Users\\dokul\\Desktop\\robot\\th_poller\\Captures\\parcels\\parcel_Seattle_12345_20251101_143022.png",
  "timestamp": "20251101_143022",
  "metro": "Seattle",
  "ocr_text": "Full text extracted from screenshot...",
  "fields": {
    "parcel_number": "1234567890",
    "owner": "JOHN DOE",
    "address": "123 MAIN ST",
    "assessed_value": "450000",
    "year_built": "1985",
    "building_sqft": "2400",
    "acres": "0.25",
    "zoning": "R-1",
    "raw_data": [...]
  }
}
```

### Batch JSON:
```json
[
  { "id": 12345, "address": "...", "fields": {...} },
  { "id": 12346, "address": "...", "fields": {...} },
  ...
]
```

## Customizing Field Extraction

The OCR extraction patterns are in `config_utils.py` → `extract_parcel_fields()`.

Edit the `patterns` dict to match your parcel website:

```python
patterns = {
    'parcel_number': [r'parcel\s*#?\s*:?\s*([A-Z0-9\-]+)'],
    'owner': [r'owner\s*:?\s*(.+?)(?:\n|$)'],
    # Add more patterns specific to your site
}
```

## Troubleshooting

### "Missing library" error
Run: `pip install -r requirements.txt`

### "tesseract is not installed"
Install Tesseract OCR (see Prerequisites #2 above)

### Chrome doesn't open
- Ensure Chrome is installed in default location
- Or install ChromeDriver manually (see Prerequisites #3)

### OCR text is garbled
- Improve screenshot quality (zoom browser, higher resolution)
- Adjust OCR preprocessing in code (grayscale, threshold, etc.)
- Wait longer than 4 seconds if page loads slowly

### No data extracted
- Check the `ocr_text` field in JSON to see raw text
- Adjust regex patterns to match your parcel site format
- Manually inspect screenshots to verify page loaded correctly

## Performance Tips

- **Reduce addresses per page**: Modify `limit: 20` in state to process fewer at once
- **Increase wait time**: Change `time.sleep(4)` to `time.sleep(6)` for slower sites
- **Run overnight**: Process large metro areas in batches using pagination

## Next Steps

After capture, you can:
1. Review JSON files and update extraction patterns
2. Upload parcel data to database via new API endpoint
3. Link `king_county_parcels_id` in `google_addresses` table
4. Generate reports on parcel ownership, values, etc.
