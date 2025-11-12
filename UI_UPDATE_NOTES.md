# UI Update: Process HTML with ChatGPT

## Changes Made

### ✅ Removed
- **"Edit Maps" button** - Removed from the main UI
- All associated map editor launching code

### ✅ Added
1. **"Process HTML with ChatGPT" button** - Replaces the Edit Maps button
2. **JSON Viewer** (`json_viewer.pyw`) - New utility to preview extracted data
3. **Automatic workflow** - Process → Preview flow

## How It Works

### User Flow:
1. **Click "Process HTML with ChatGPT"** button in the main UI
2. **Processing happens** - Script runs in background
3. **Status updates** - Shows in the status bar:
   - "Processing HTML with ChatGPT..."
   - "Processing complete! Opening JSON viewer..."
4. **JSON Viewer opens** - Automatically shows extracted listings

### JSON Viewer Features:
- ✅ **Table view** - Shows all listings in a sortable table
- ✅ **Columns**: ID, Title, Beds, Baths, Sqft, Price, Address, Network
- ✅ **Details panel** - Click any row to see full JSON
- ✅ **Refresh button** - Reload the data
- ✅ **Close button** - Exit the viewer

## What Gets Processed

The button triggers `process_daily_captures.py` which:
1. Finds today's `Captures/YYYY-MM-DD/` folder
2. Processes all `.html` files
3. Uses ChatGPT to extract apartment listings
4. Downloads images to `Captures/images/`
5. Creates `extracted_listings.json`
6. Upserts to `apartment_listings` MySQL table

## JSON Viewer Interface

```
┌────────────────────────────────────────────────┐
│ 📊 Extracted Listings Preview    12 listings  │
│                            [Refresh] [Close]   │
├────────────────────────────────────────────────┤
│ ID         │ Title      │ Beds │ Price │ Addr │
│ abc-123    │ Studio Apt │ 0    │ $1200 │ ...  │
│ def-456    │ 1BR Modern │ 1    │ $1650 │ ...  │
│ ...        │ ...        │ ...  │ ...   │ ...  │
├────────────────────────────────────────────────┤
│ Details:                                       │
│ {                                              │
│   "id": "abc-123",                            │
│   "title": "Studio Apartment",                │
│   "bedrooms": "0",                            │
│   "price": "$1200",                           │
│   ...                                         │
│ }                                             │
└────────────────────────────────────────────────┘
```

## Files Modified

1. **config_utils.py**
   - Removed: `open_map_editor()` function and "Edit Maps" button
   - Added: `process_html_with_chatgpt()` function and new button
   - Added: Threading for background processing
   - Added: Auto-launch JSON viewer after processing

2. **json_viewer.pyw** (NEW)
   - Table view of extracted listings
   - Details panel showing full JSON
   - Refresh and close buttons
   - Can be launched standalone or from UI

## Usage

### From Main UI:
1. Click **"Process HTML with ChatGPT"**
2. Wait for processing (status bar shows progress)
3. JSON viewer opens automatically

### Standalone JSON Viewer:
```powershell
python json_viewer.pyw
# Or with specific file:
python json_viewer.pyw "Captures\2025-10-22\extracted_listings.json"
```

## Requirements

Already installed if you have the daily processor:
- `openai` package
- `OPENAI_API_KEY` environment variable
- `process_daily_captures.py` script

## Benefits

✅ **Simpler workflow** - One button does everything  
✅ **Visual feedback** - See extracted data immediately  
✅ **No manual steps** - Fully automated process → preview  
✅ **Quick validation** - Verify extraction quality instantly  
✅ **Better UX** - Clear, modern interface  

## Backward Compatibility

The Map Editor (`map_editor.pyw`) still exists and can be launched manually if needed:
```powershell
python map_editor.pyw
```

But the main UI now focuses on the automated ChatGPT workflow.

---

**Status:** ✅ Complete and ready to use  
**Date:** October 22, 2025
