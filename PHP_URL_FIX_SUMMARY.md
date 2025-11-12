# PHP URL Fix Summary

## Problem
The URL `http://localhost/process_html_with_openai.php` wasn't opening because all Python code had hardcoded `http://localhost/` URLs, but the PHP server is now running on `http://localhost:8000/`.

## Solution
Updated all Python files to use the `php_url()` helper function from `config_core.py`, which reads the configured PHP_BASE_URL from `php_config.env`.

## Files Updated

### 1. config_hud.py (14 URLs fixed)
- Line 3953: `get_empty_parcels_list.php`
- Line 4172: `get_major_metros.php`
- Line 4775: `get_accounts.php`
- Line 4818: `get_code_cities.php`
- Line 4856: `get_911_cities.php`
- Line 5279: `get_accounts.php` (search)
- Line 7137: `queue_step_api.php`
- Line 8625: `send_price_changes.php`
- Line 8657: `send_new_listings.php`
- Line 8721: `send_email_api.php`
- Line 8899: `queue_step_api.php`
- Line 9603: `process_html_with_openai.php`

### 2. config_address_match.py (3 URLs fixed)
- Line 592: `find_or_create_place.php` (place_id)
- Line 596: `find_or_create_place.php` (address)
- Line 1560: `queue_step_api.php`

### 3. config_helpers.py (3 URLs fixed)
- Line 1119: `find_or_create_place.php` (place_id)
- Line 1123: `find_or_create_place.php` (address)
- Line 3089: `queue_step_api.php`

### 4. worker.py (1 URL fixed)
- Line 452: `process_html_with_openai.php`
- Added import: `from config_core import php_url`

### 5. config_hud_steps.py (1 URL fixed)
- Line 313: `process_html_with_openai.php`

## Total Changes
- **5 files updated**
- **22 hardcoded URLs replaced**
- All now use `php_url()` helper function

## How It Works

**Before:**
```python
url = "http://localhost/process_html_with_openai.php"
```

**After:**
```python
url = php_url("process_html_with_openai.php")
```

The `php_url()` function:
1. Reads `PHP_BASE_URL` from `php_config.env`
2. Currently set to: `http://localhost:8000`
3. Builds full URL: `http://localhost:8000/process_html_with_openai.php`

## Configuration File
`php_config.env`:
```ini
PHP_BASE_URL=http://localhost:8000
```

To switch back to XAMPP, change to:
```ini
PHP_BASE_URL=http://localhost
```

## Next Steps
1. **Restart the Python application** (config_hud.py)
2. The application will now use `http://localhost:8000` for all PHP calls
3. All PHP functionality should work correctly

## Testing
- PHP server verified running: ✅ HTTP 200 (5187 bytes)
- All URLs now dynamically configured: ✅
- No compile errors in updated files: ✅

## Current Status
✅ **PHP server running on port 8000**
✅ **All Python code updated to use php_url()**
✅ **Configuration system in place**
⏳ **Waiting for Python application restart**
