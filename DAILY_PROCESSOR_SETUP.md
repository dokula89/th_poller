# 🏢 Daily Apartment Listing Processor - Complete Setup

## 📦 What Was Created

### 1. **process_daily_captures.py** (Main Script)
   - Processes HTML files from today's `Captures/YYYY-MM-DD/` folder
   - Uses ChatGPT to extract apartment listings
   - Downloads and saves images
   - Upserts to `apartment_listings` MySQL table
   - Creates JSON backup

### 2. **test_daily_processor.py** (Test Script)
   - Dry-run mode for testing
   - Tests URL ID extraction
   - Tests HTML processing without DB writes
   - Saves output to `test_extraction_output.json`

### 3. **run_daily_processor.ps1** (Convenience Runner)
   - One-click execution
   - Checks for API key
   - Shows colored output
   - Waits for keypress at end

### 4. **DAILY_PROCESSOR_README.md** (Full Documentation)
   - Complete setup instructions
   - Usage examples
   - Troubleshooting guide
   - Cost estimation

## 🚀 Quick Start

### Step 1: Install Dependencies
```powershell
pip install openai requests mysql-connector-python
```

### Step 2: Set API Key
```powershell
[System.Environment]::SetEnvironmentVariable('OPENAI_API_KEY', 'sk-your-key-here', 'User')
```

### Step 3: Test It
```powershell
python test_daily_processor.py
```

### Step 4: Run It
```powershell
.\run_daily_processor.ps1
```

## 🎯 How It Works

```
📁 Captures/2025-10-22/networks_1.html
          ↓
   🤖 ChatGPT Analysis
          ↓
   📊 Extract Listings
          ↓
   🖼️ Download Images → Captures/images/
          ↓
   💾 Upsert to MySQL (apartment_listings)
          ↓
   ✅ Done! (+ JSON backup)
```

## 📋 Features

✅ **Auto-Detection**: Finds today's folder automatically  
✅ **AI-Powered**: GPT-4 extracts structured data  
✅ **Smart IDs**: Extracts unique IDs from URLs  
✅ **Image Handling**: Downloads and saves thumbnails  
✅ **Upsert Logic**: Insert new, update existing  
✅ **JSON Backup**: Saves extracted data  
✅ **Error Handling**: Graceful failures with logs  
✅ **Cost Effective**: < 1¢ per file  

## 📊 Data Extracted

From each listing:
- 🔗 Listing URL (for unique ID)
- 🏠 Title, description
- 🛏️ Bedrooms, bathrooms
- 📏 Square footage
- 💰 Price
- 📍 Full address (street, city, state)
- 🖼️ Images (downloaded)
- 📅 Available date
- 📞 Contact info
- 🔗 Application link

## 🗂️ Database Schema

Updates `apartment_listings` table with:
- `id` - Unique identifier from URL
- `network` - Source HTML filename
- `time_created` - First insert timestamp
- `time_updated` - Last update timestamp
- + All extracted fields

## 🔄 Automation Options

### Option 1: Manual Run
```powershell
.\run_daily_processor.ps1
```

### Option 2: Scheduled Task
- Open Task Scheduler
- Create daily task at 11 PM
- Run: `python process_daily_captures.py`

### Option 3: Integration
Add to existing poller workflow:
```python
# At end of poller script
import subprocess
subprocess.run(['python', 'process_daily_captures.py'])
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| No API key | Set `OPENAI_API_KEY` environment variable |
| Import errors | Run `pip install openai requests mysql-connector-python` |
| No folder found | Check `Captures/YYYY-MM-DD/` exists |
| Database error | Verify MySQL running and credentials in `config_utils.py` |
| AI extraction fails | Check API key is valid and has credits |

## 💰 Cost

- Model: `gpt-4o-mini`
- Rate: $0.15 per 1M tokens
- Per file: ~$0.001 (< 1 cent)
- Daily: < $0.01 typically

## 📝 Example Output

```
============================================================
Daily Capture Processor
============================================================

📁 Processing folder: Captures\2025-10-22
Found 1 HTML file(s)

📄 Processing: networks_1.html
  📍 Source URL: https://example.com/listings
  → Sending HTML to ChatGPT for analysis...
  ✓ Extracted 12 listings from HTML
  ✓ Downloaded image: ba786613_a1b2c3d4.jpg
  ✓ Listing 1: Spacious 1BR - ID: ba786613-8954-447d

💾 Saved backup: extracted_listings.json

💾 Upserting 12 listings to database...
  ✓ Inserted: Spacious 1BR (ID: ba786613-8954-447d)
  ↻ Updated: Modern Studio (ID: f9e8d7c6-5432-1a2b)

✅ Database updated: 10 inserted, 2 updated
============================================================
✅ Processing complete: 12 listings processed
============================================================
```

## 🔗 Integration with Map Editor

This script complements the Map Editor:

1. **Map Editor**: Manual field mapping, one-time setup
2. **Daily Processor**: Automated extraction, daily runs
3. **Use both**: Map Editor for complex sites, Processor for routine updates

## ✨ Next Steps

1. ✅ Test with: `python test_daily_processor.py`
2. ✅ Run once: `.\run_daily_processor.ps1`
3. ✅ Check database and images
4. ✅ Schedule daily task
5. ✅ Monitor and adjust

## 📚 Files Reference

- `process_daily_captures.py` - Main processor
- `test_daily_processor.py` - Test/dry-run
- `run_daily_processor.ps1` - PowerShell runner
- `DAILY_PROCESSOR_README.md` - Full documentation
- `AI_MAPPING_SETUP.md` - Map Editor AI setup

---

**Created:** October 22, 2025  
**Status:** ✅ Ready to use
