# Parcel Automation - Batch Processing Integration

## Current Status

✅ **Completed:**
1. Extraction method selector added to "Process All Addresses" tab
   - Radio buttons for OpenAI vs BeautifulSoup
2. OCR improvements (6x upscaling, orange background handling)
3. Copy buttons (Copy All / Copy Selected)
4. Improved OCR patterns for typos

⚠️ **In Progress:**
- Integrating batch processing methods into parcel_automation.py

## What You Need

The system needs these methods added to the `ParcelAutomationWindow` class:

### 1. `process_parcel_images_batch()` 
- Checks for unprocessed images in `Captures/parcels/`
- Routes to OpenAI or BeautifulSoup based on selection

### 2. `process_with_openai_batch()`
- Waits for 20 unprocessed images
- Sends to OpenAI Vision API
- Saves JSON results
- Inserts to database with google_addresses linkage
- Renames images to `*_processed.png`

### 3. `insert_batch_to_database()`
- Inserts into `king_county_parcels` table
- Links with `google_addresses` table via IDs
- Extracts google_addresses_id from image filename

## Manual Integration Steps

Since automated injection is having issues, here's what to do:

1. **Open `parcel_automation.py`**

2. **Find the `process_all_addresses` method** (around line 480)

3. **Replace it with:**
```python
def process_all_addresses(self):
    from pathlib import Path
    parcels_dir = Path("Captures/parcels")
    unprocessed = [img for img in parcels_dir.glob("parcels_*.png") 
                   if not img.stem.endswith('_processed')]
    
    if unprocessed:
        self.log_activity(f"Found {len(unprocessed)} saved images")
        self.process_parcel_images_batch()
        return
    
    # Original batch automation code...
```

4. **Add these methods before `launch_parcel_automation` function:**

See the complete methods in `process_with_openai.py` - they work standalone.

## Quick Test

1. Save 2 parcel images as `parcels_123.png` and `parcels_124.png`
2. Set API key: `$env:OPENAI_API_KEY="your-key"`
3. Open automation window
4. Go to "Process All Addresses" tab
5. Select "OpenAI Vision API"
6. Click "Process All Addresses"

Should process when you have 20+ images.

## Alternative: Use Standalone Script

The `process_with_openai.py` script works perfectly standalone:

```powershell
$env:OPENAI_API_KEY="your-key"
python process_with_openai.py
```

It does everything:
- Processes images in batches of 20
- Saves JSON
- Inserts to database with linkage
- Renames processed images

You can keep using this until we properly integrate it into the GUI.

## Files Created

- `process_with_openai.py` - Standalone OpenAI processor (WORKING)
- `batch_processor_gui.py` - Standalone GUI (WORKING)
- `add_method_selector.py` - Adds radio buttons (APPLIED)
- Various injection scripts (had string literal issues)

## Next Session

To finish integration:
1. Manually copy methods from `process_with_openai.py` into `ParcelAutomationWindow` class
2. Or continue using standalone `process_with_openai.py` (it works great!)
3. Test with 20+ real parcel images
