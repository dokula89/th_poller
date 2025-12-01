# Parcel Automation Setup Guide

This guide explains how to set up and use the parcel automation feature.

## Prerequisites

### 1. Install Tesseract OCR

Tesseract is required for extracting text from screenshots.

**Download and Install:**
1. Download Tesseract installer for Windows: https://github.com/UB-Mannheim/tesseract/wiki
2. Install to default location: `C:\Program Files\Tesseract-OCR`
3. Add to PATH environment variable:
   - Right-click "This PC" → Properties → Advanced System Settings
   - Click "Environment Variables"
   - Under "System variables", find and edit "Path"
   - Add: `C:\Program Files\Tesseract-OCR`
   - Click OK to save

**Verify Installation:**
```powershell
tesseract --version
```

### 2. Python Packages

The required Python packages should already be installed:
- `pillow` - Image processing
- `pyautogui` - UI automation
- `pytesseract` - OCR wrapper for Tesseract
- `pygetwindow` - Window management

If not installed, run:
```powershell
pip install pillow pyautogui pytesseract pygetwindow
```

## How to Use

### 1. Open Parcel Tab
- Click on the "Parcel" tab in the main application
- Select a metro from the dropdown (e.g., Seattle)
- Parcel records will load in the table

### 2. Start Automation
- Click the **play button (▶)** in the ID column of any parcel row
- An automation window will open showing the automation steps

### 3. Automation Workflow

The automation will:

1. **Open Parcel Viewer** - Opens the parcel viewer website in your default browser
2. **Position Browser** - Moves browser window to right 80% of screen
3. **Enter Address** - Automatically types the parcel address into the search field
4. **Submit Search** - Presses Enter to search
5. **Wait for Results** - Allows time for the page to load
6. **Capture Screenshot** - Takes a screenshot of the browser window
7. **Process with OCR** - Extracts text from the screenshot using Tesseract
8. **Extract Data** - Parses the OCR text to find structured parcel data
9. **Save Results** - Saves data to `Captures/parcels/parcels.json`

### 4. Output Files

**Screenshots:**
- Location: `C:\Users\dokul\Desktop\robot\th_poller\Captures\parcels\`
- Filename format: `parcel_{id}_{timestamp}.png`
- Example: `parcel_14_20251112_143052.png`

**JSON Data:**
- Location: `C:\Users\dokul\Desktop\robot\th_poller\Captures\parcels\parcels.json`
- Format: Array of parcel records with extracted data

### 5. JSON Structure

Each parcel entry in `parcels.json` contains:

```json
{
  "id": 14,
  "address": "4801 FAUNTLEROY WAY SW 98116",
  "metro": "Seattle",
  "parcel_link": "https://gismaps.kingcounty.gov/parcelviewer2/",
  "timestamp": "2025-11-12T14:30:52",
  "screenshot": "C:\\Users\\dokul\\Desktop\\robot\\th_poller\\Captures\\parcels\\parcel_14_20251112_143052.png",
  "raw_text": "...full OCR text...",
  "extracted_fields": {
    "parcel_number": "6126600800",
    "owner": "CORNELL & ASSOCIATES",
    "assessed_value": "14,029,000",
    "lot_size": "9,000",
    "year_built": "2015",
    "zoning": "NC3-40"
  }
}
```

## Troubleshooting

### Tesseract Not Found
**Error:** `pytesseract.pytesseract.TesseractNotFoundError`

**Solution:** Set Tesseract path explicitly in `parcel_automation.py`:
```python
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
```

### Browser Window Not Positioning
**Issue:** Browser stays in wrong position

**Solutions:**
- Make sure browser window is not maximized when automation starts
- Try different browser (Chrome works best)

### OCR Accuracy Issues
**Issue:** Extracted text is inaccurate

**Solutions:**
- Increase screenshot size/quality
- Wait longer for page to fully render
- Check logs at `logs\parcel_automation.log`

## Logs

Automation logs: `C:\Users\dokul\Desktop\robot\th_poller\logs\parcel_automation.log`
