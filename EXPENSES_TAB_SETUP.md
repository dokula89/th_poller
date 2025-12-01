# Expenses Tab - API Usage Tracking

## Overview
Added a new **💰 Expenses** tab to the Database Sync window that tracks Google API and OpenAI API usage with cost calculations.

## Features

### 1. **API Usage Summary**
- Real-time cost tracking for OpenAI and Google APIs
- Total calls and cost per service
- Combined total cost across all services

### 2. **Detailed API Call Log**
- Recent 100 API calls displayed in a table
- Shows:
  - Date/Time of call
  - Service (OpenAI/Google)
  - Endpoint used
  - Tokens/Calls count
  - Cost in USD
- Color-coded by service (Orange for OpenAI, Blue for Google)

### 3. **Database Table: `api_calls`**
```sql
CREATE TABLE api_calls (
    id INT AUTO_INCREMENT PRIMARY KEY,
    service VARCHAR(50) NOT NULL,           -- 'openai' or 'google'
    endpoint VARCHAR(100) NOT NULL,         -- e.g., 'chat.completions', 'places_details'
    call_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tokens_used INT DEFAULT 0,              -- Total tokens (OpenAI only)
    calls_count INT DEFAULT 1,              -- Number of API calls (Google)
    input_tokens INT DEFAULT 0,             -- Input tokens (OpenAI)
    output_tokens INT DEFAULT 0,            -- Output tokens (OpenAI)
    model VARCHAR(50),                      -- Model name (OpenAI)
    cost_usd DECIMAL(10, 6) DEFAULT 0,      -- Calculated cost
    metadata TEXT,                          -- Additional info as JSON
    INDEX idx_service (service),
    INDEX idx_call_time (call_time)
)
```

## Pricing (as of 2025)

### OpenAI Models
| Model | Input Cost | Output Cost |
|-------|-----------|-------------|
| gpt-4o | $0.0025 / 1K tokens | $0.01 / 1K tokens |
| gpt-4o-mini | $0.00015 / 1K tokens | $0.0006 / 1K tokens |
| gpt-4-vision-preview | $0.01 / 1K tokens | $0.03 / 1K tokens |
| gpt-4 | $0.03 / 1K tokens | $0.06 / 1K tokens |
| gpt-3.5-turbo | $0.0005 / 1K tokens | $0.0015 / 1K tokens |

### Google Maps APIs
| API | Cost per Call |
|-----|--------------|
| Places Details | $0.017 |
| Places Search | $0.032 |
| Places Nearby | $0.032 |
| Geocoding | $0.005 |

## Implementation

### Files Created/Modified

1. **`track_api_usage.py`** - Python helper for tracking API usage
   - `log_openai_call()` - Log OpenAI API calls
   - `log_google_call()` - Log Google API calls
   - `get_total_costs()` - Get summary statistics

2. **`track_api_usage.php`** - PHP helper for tracking API usage
   - `log_google_api_call()` - Log Google API calls from PHP
   - `get_total_api_costs()` - Get summary statistics

3. **`config_hud.py`** - Added Expenses tab
   - Line ~8180: New tab added after Sync Log tab
   - Real-time cost display
   - Recent calls log with auto-refresh

4. **`process_with_openai.py`** - Integrated OpenAI tracking
   - Line ~110: Added tracking after API response
   - Logs model, tokens, response time, image count

5. **`htdocs/step5/find_or_create_place.php`** - Integrated Google tracking
   - Line ~157: Included tracking helper
   - Line ~311: Track Places Details API calls
   - Line ~2577: Track Geocoding API calls

## Usage

### Accessing the Tab
1. Open Database Sync window from the HUD
2. Click on **💰 Expenses** tab
3. View real-time API usage and costs

### Refreshing Data
- Click **🔄 Refresh Data** button to reload latest stats
- Tab auto-loads on first open

### Python API Tracking
```python
from track_api_usage import log_openai_call, log_google_call

# Log OpenAI call
log_openai_call(
    model="gpt-4o",
    input_tokens=1000,
    output_tokens=500,
    endpoint="chat.completions",
    metadata={"images_processed": 5}
)

# Log Google call
log_google_call(
    endpoint="places_details",
    calls_count=1,
    metadata={"place_id": "ChIJ..."}
)
```

### PHP API Tracking
```php
require_once __DIR__ . '/track_api_usage.php';

// Log Google API call
log_google_api_call($mysqli, 'places_details', 1, [
    'place_id' => $place_id,
    'ga_id' => $ga_id
]);
```

## Testing

Test the tracking system:

```bash
# Test Python tracking
python track_api_usage.py

# View in database
mysql -u root -e "SELECT * FROM offta.api_calls ORDER BY call_time DESC LIMIT 10;"
```

## Benefits

1. **Cost Monitoring**: Track exactly how much you're spending on API calls
2. **Usage Analytics**: See which endpoints are called most frequently
3. **Debugging**: Identify excessive API usage or errors
4. **Budgeting**: Plan API budgets based on historical usage
5. **Optimization**: Find opportunities to reduce API costs

## Future Enhancements

- [ ] Daily/weekly/monthly cost summaries
- [ ] Cost alerts when threshold exceeded
- [ ] Export usage data to CSV/Excel
- [ ] Chart visualizations (cost over time, usage by endpoint)
- [ ] Cost projections based on trends
- [ ] API quota tracking
