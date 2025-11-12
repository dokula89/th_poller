#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step execution methods (_step_*)
Extracted from config_hud.py (lines 5465-6327)
"""

from config_core import *
from config_hud_db import update_db_status
from config_helpers import launch_manual_browser, launch_manual_browser_docked_right, launch_manual_browser_docked_left

class HUDSteps:
    """Mixin class for step execution methods"""
    
    def _step_capture_html(self, job_id, link, the_css="", table_name: str | None = None):
        """Step 1: Capture HTML from the URL"""
        log_to_file(f"[Queue] Capturing HTML for job {job_id} from {link}")
        
        # Sanitize CSS selector - remove invalid characters like quotes
        if the_css:
            original_css = the_css
            the_css = the_css.replace('"', '').replace("'", '').strip()
            if the_css != original_css:
                log_to_file(f"[Queue] CSS selector sanitized from '{original_css}' to '{the_css}'")
        
        log_to_file(f"[Queue] CSS selector: {the_css}")
        
        # Open the link in Chrome (or default browser) for manual visibility as soon as Step 1 starts,
        # aligned docked to the right (25% from left, full height). Skip if already opened at click time.
        try:
            # Avoid duplicate open if UI handler already launched it for this job
            if not (hasattr(self, '_opened_browser_for_job') and str(job_id) in getattr(self, '_opened_browser_for_job', set())):
                if isinstance(link, str) and link.startswith("http"):
                    try:
                        launch_manual_browser_docked_right(link)
                    except Exception:
                        launch_manual_browser(link)
        except Exception as _open_err:
            log_to_file(f"[Queue] Warning: failed to open browser for link: {_open_err}")
        
        # Check internet connection first
        if not self._check_internet_connection():
            error_msg = "No internet connection available. Please check your network and try again."
            log_to_file(f"[Queue] {error_msg}")
            self._root.after(0, lambda: self._show_error_popup("No Internet Connection", error_msg))
            raise Exception(error_msg)
        
        # Get the full page HTML
        response = requests.get(link, timeout=30)
        
        # Check for 403 Forbidden error
        manual_html_captured = False
        if response.status_code == 403:
            log_to_file(f"[Queue] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            log_to_file(f"[Queue] ⚠️  403 FORBIDDEN ERROR DETECTED")
            log_to_file(f"[Queue] URL: {link}")
            log_to_file(f"[Queue] Status Code: {response.status_code}")
            log_to_file(f"[Queue] Starting automated capture process...")
            log_to_file(f"[Queue] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            if not the_css:
                error_msg = "403 Forbidden and no CSS selector provided. Cannot capture element."
                log_to_file(f"[Queue] {error_msg}")
                try:
                    self._root.after(0, lambda: self._show_error_popup("Missing CSS Selector", error_msg))
                except:
                    pass
                raise Exception(error_msg)
            
            log_to_file(f"[Queue] Step 1/3: Opening Chrome browser (20% from left, 80% width, 25% zoom)")
            log_to_file(f"[Queue] CSS selector to capture: {the_css}")
            
            # Log screen size for debugging
            import ctypes
            user32 = ctypes.windll.user32 if hasattr(ctypes, 'windll') else None
            if user32:
                screen_w = user32.GetSystemMetrics(0)
                screen_h = user32.GetSystemMetrics(1)
                calc_x = int(screen_w * 0.20)
                calc_w = int(screen_w * 0.80)
                log_to_file(f"[Queue] Screen size: {screen_w}x{screen_h}")
                log_to_file(f"[Queue] Calculated Chrome window: position=({calc_x}, 0), size=({calc_w}x{screen_h})")
            
            # Open in Chrome at 20% from left side, 80% width, 20% zoom with DevTools auto-opened
            try:
                launch_manual_browser_docked_left(link, left_offset_ratio=0.20, width_ratio=0.80, zoom_percent=20.0, auto_open_devtools=True)
            except Exception:
                launch_manual_browser(link)
            
            # Wait for Chrome and page to load
            import time
            log_to_file(f"[Queue] Waiting 4 seconds for Chrome and page to load...")
            time.sleep(4)
            
            # Use pyautogui to automate finding and copying the element from DevTools
            try:
                import pyautogui
                log_to_file(f"[Queue] Step 2/3: Automating DevTools to find and copy element")
                
                # Click in the center-right of screen to focus Chrome window (not the activity window on left)
                screen_w = user32.GetSystemMetrics(0) if user32 else 1920
                screen_h = user32.GetSystemMetrics(1) if user32 else 1080
                chrome_center_x = int(screen_w * 0.60)  # 60% from left (middle of the 80% chrome window)
                chrome_center_y = int(screen_h * 0.50)  # 50% from top (middle of screen)
                log_to_file(f"[Queue] → Clicking Chrome window to focus at ({chrome_center_x}, {chrome_center_y})")
                pyautogui.click(chrome_center_x, chrome_center_y)
                time.sleep(0.5)  # Wait for Chrome to focus
                
                # Press F12 to open DevTools
                log_to_file(f"[Queue] → Opening DevTools (F12)")
                pyautogui.press('f12')
                time.sleep(1.0)  # Reduced from 1.5
                
                # Press Ctrl+F to open search in DevTools
                log_to_file(f"[Queue] → Opening search (Ctrl+F)")
                pyautogui.hotkey('ctrl', 'f')
                time.sleep(0.3)  # Reduced from 0.5
                
                # Type the CSS selector to search for it
                log_to_file(f"[Queue] → Searching for: {the_css}")
                pyautogui.write(the_css, interval=0.03)  # Faster typing
                time.sleep(0.3)  # Reduced from 0.5
                
                # Press Enter to find the element
                log_to_file(f"[Queue] → Finding element (Enter)")
                pyautogui.press('enter')
                time.sleep(0.3)  # Reduced from 0.5
                
                # Press Escape to close the search box
                log_to_file(f"[Queue] → Closing search (Escape)")
                pyautogui.press('escape')
                time.sleep(0.2)  # Reduced from 0.3
                
                # Right-click on the highlighted element
                log_to_file(f"[Queue] → Right-clicking element")
                pyautogui.rightClick()
                time.sleep(0.3)  # Reduced from 0.5
                
                # Type 'Copy' to navigate to Copy menu
                log_to_file(f"[Queue] → Navigating to Copy menu")
                pyautogui.press('c')
                time.sleep(0.2)  # Reduced from 0.3
                
                # Press Down arrow twice to get to "Copy element"
                log_to_file(f"[Queue] → Selecting 'Copy element'")
                pyautogui.press('down')
                time.sleep(0.05)  # Reduced from 0.1
                pyautogui.press('down')
                time.sleep(0.05)  # Reduced from 0.1
                
                # Press Enter to copy the element HTML
                log_to_file(f"[Queue] → Copying element to clipboard (Enter)")
                pyautogui.press('enter')
                time.sleep(0.3)  # Reduced from 0.5
                
                # Get HTML from clipboard using main thread
                log_to_file(f"[Queue] Step 3/3: Reading HTML from clipboard")
                html_content_holder = [None]
                
                def get_clipboard_content():
                    try:
                        html_content_holder[0] = self._root.clipboard_get()
                        log_to_file(f"[Queue] ✓ Captured {len(html_content_holder[0])} characters from clipboard")
                    except Exception as clip_err:
                        log_to_file(f"[Queue] ✗ Failed to read clipboard: {clip_err}")
                        html_content_holder[0] = None
                
                self._root.after(0, get_clipboard_content)
                # Wait for clipboard read to complete
                time.sleep(0.5)  # Reduced from 1.0
                html_content = html_content_holder[0]
                
                if html_content and len(html_content) > 100:
                    # HTML is already the copied element from DevTools - no need to parse again
                    log_to_file(f"[Queue] ✓ Element captured successfully from DevTools")
                    log_to_file(f"[Queue] ✓ Element size: {len(html_content)} characters")
                    manual_html_captured = True
                else:
                    error_msg = f"Failed to capture HTML automatically from clipboard. Length: {len(html_content) if html_content else 0}"
                    log_to_file(f"[Queue] ✗ {error_msg}")
                    try:
                        self._root.after(0, lambda: self._show_error_popup("Capture Failed", error_msg))
                    except:
                        pass
                    raise Exception(error_msg)
                    
            except Exception as auto_err:
                error_msg = f"Automatic capture failed: {auto_err}"
                log_to_file(f"[Queue] ERROR: {error_msg}")
                import traceback
                log_to_file(f"[Queue] ERROR: Traceback: {traceback.format_exc()}")
                try:
                    self._root.after(0, lambda: self._show_error_popup("Automation Error", error_msg))
                except:
                    pass
                raise Exception(error_msg)
        
        # Only do automated capture if we didn't get manual HTML
        if not manual_html_captured:
            response.raise_for_status()
            html_content = response.text
        
            # If CSS selector is provided, extract that specific element
            if the_css:
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html_content, 'html.parser')
                    
                    # Try to find the element with the CSS selector
                    element = soup.select_one(the_css)
                    if element:
                        html_content = str(element)
                        log_to_file(f"[Queue] Extracted element matching CSS: {the_css}")
                    else:
                        log_to_file(f"[Queue] Warning: CSS selector '{the_css}' not found, using full HTML")
                except Exception as e:
                    log_to_file(f"[Queue] Warning: Failed to apply CSS selector: {e}, using full HTML")
        
        # Save HTML to file
        date_str = datetime.now().strftime("%Y-%m-%d")
        html_dir = BASE_DIR / date_str
        
        log_to_file(f"[Queue] Creating directory: {html_dir}")
        ensure_dir(html_dir)
        log_to_file(f"[Queue] ✓ Directory created/exists")
        
        # Determine table name without touching Tk variables from a background thread
        if not table_name:
            try:
                # Best-effort: avoid .get() on Tk variables
                table_name = getattr(self, '_current_table', None)
                if hasattr(table_name, 'get'):
                    # This may raise in background threads; guard it
                    table_name = table_name.get()  # type: ignore[attr-defined]
                if not isinstance(table_name, str) or not table_name:
                    table_name = "queue"
            except Exception as _e:
                log_to_file(f"[Queue] Unable to read table name from UI (ok): {_e}")
                table_name = "queue"
        log_to_file(f"[Queue] Current table: {table_name}")
        
        # Derive filename prefix from table. Special rule: websites are saved under 'networks'.
        original_table = str(table_name).lower()
        prefix = original_table
        # Force websites -> networks per user requirement
        if original_table in ("queue_websites", "listing_websites", "websites"):
            prefix = "networks"
        else:
            # For tables like listing_networks or queue_networks, keep the suffix
            if "_" in original_table:
                parts = original_table.split("_")
                # Use the last segment as a sane default (e.g., listing_networks -> networks)
                prefix = parts[-1]
        log_to_file(f"[Queue] Filename prefix resolved: {prefix} (from table '{original_table}')")
        
        html_file = html_dir / f"{prefix}_{job_id}.html"
        log_to_file(f"[Queue] Writing HTML to: {html_file}")
        log_to_file(f"[Queue] HTML content length: {len(html_content)} bytes")
        
        html_file.write_text(html_content, encoding='utf-8')
        
        log_to_file(f"[Queue] ✓✓✓ HTML SAVED SUCCESSFULLY to {html_file}")
        log_to_file(f"[Queue] File exists: {html_file.exists()}")
        log_to_file(f"[Queue] File size: {html_file.stat().st_size if html_file.exists() else 0} bytes")
        
        # Close Chrome if it was opened for 403 handling
        if manual_html_captured:
            try:
                import pyautogui
                log_to_file(f"[Queue] Closing Chrome window...")
                pyautogui.hotkey('alt', 'f4')
                log_to_file(f"[Queue] ✓ Chrome closed")
            except Exception as close_err:
                log_to_file(f"[Queue] Warning: Failed to close Chrome: {close_err}")
        
        return str(html_file)
    
    def _step_create_json(self, job_id, link, table_name: str | None = None):
        """Step 2: Create JSON using process_html_with_openai.php"""
        log_to_file(f"[Queue] ========== CREATE JSON START ==========")
        log_to_file(f"[Queue] Creating JSON for job {job_id}")
        
        # Get the HTML file path - need to find it since we don't know the table name here
        date_str = datetime.now().strftime("%Y-%m-%d")
        html_dir = BASE_DIR / date_str
        
        log_to_file(f"[Queue] Looking for HTML file in: {html_dir}")
        log_to_file(f"[Queue] Pattern: *_{job_id}.html")
        
        # Look for HTML file with any prefix matching the job_id
        html_file = None
        for f in html_dir.glob(f"*_{job_id}.html"):
            html_file = f
            log_to_file(f"[Queue] Found matching file: {f}")
            break
        
        if not html_file or not html_file.exists():
            error_msg = f"HTML file not found in {html_dir}/*_{job_id}.html - run Step 1 first"
            log_to_file(f"[Queue] ERROR: {error_msg}")
            raise Exception(error_msg)
        
        log_to_file(f"[Queue] ✓ Found HTML file: {html_file}")
        log_to_file(f"[Queue] File size: {html_file.stat().st_size} bytes")
        
        # Call the PHP script via localhost
        from urllib.parse import quote
        import requests
        
        # Use forward slashes for URL encoding
        file_path_for_url = str(html_file).replace('\\', '/')
        file_path_encoded = quote(file_path_for_url)
        # Add headless=1 parameter to get JSON response directly instead of HTML interface
        php_api_url = php_url(f"process_html_with_openai.php?file={file_path_encoded}&model=gpt-4o-mini&method=local&process=1&headless=1")
        
        log_to_file(f"[Queue] ========== CALLING PHP SCRIPT ==========")
        log_to_file(f"[Queue] URL: {php_api_url}")
        log_to_file(f"[Queue] Original path: {html_file}")
        log_to_file(f"[Queue] Encoded path: {file_path_encoded}")
        log_to_file(f"[Queue] Starting request (timeout=120s)...")
        
        # Print the URL to console as well for easy copy-paste
        print(f"\n{'='*80}")
        print(f"[2.JSON] Calling PHP Script:")
        print(f"URL: {php_api_url}")
        print(f"{'='*80}\n")
        
        # Update UI to show we're calling PHP
        def _update_status_calling():
            self._queue_status_label.config(text=f"📞 Calling OpenAI PHP script for job {job_id}...")
        self._root.after(0, _update_status_calling)
        
        try:
            response = requests.get(php_api_url, timeout=120)  # 2 minute timeout for AI processing
            log_to_file(f"[Queue] ✓ Response received!")
            log_to_file(f"[Queue] Status code: {response.status_code}")
            log_to_file(f"[Queue] Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            log_to_file(f"[Queue] Response length: {len(response.text)} chars")
            log_to_file(f"[Queue] First 200 chars: {response.text[:200]}")
            
            # Update UI to show response received
            def _update_status_received():
                self._queue_status_label.config(text=f"✓ Got response from PHP ({len(response.text)} chars)...")
            self._root.after(0, _update_status_received)
            
            response.raise_for_status()
        except requests.Timeout:
            error_msg = "PHP script timed out after 120 seconds"
            log_to_file(f"[Queue] ERROR: {error_msg}")
            
            def _show_timeout():
                self._queue_status_label.config(text=f"⏱️ TIMEOUT: PHP took >120s for job {job_id}")
            self._root.after(0, _show_timeout)
            
            raise Exception(error_msg)
        except requests.RequestException as req_err:
            error_msg = f"HTTP request failed: {req_err}"
            log_to_file(f"[Queue] ERROR: {error_msg}")
            
            def _show_http_error():
                self._queue_status_label.config(text=f"🌐 HTTP Error: {str(req_err)[:50]}")
            self._root.after(0, _show_http_error)
            
            raise Exception(error_msg)
        
        # Check if response is HTML (error page) or JSON
        content_type = response.headers.get('Content-Type', '')
        if 'text/html' in content_type or response.text.strip().startswith('<!'):
            error_msg = f"PHP returned HTML page instead of JSON. Check if headless=1 parameter is working."
            log_to_file(f"[Queue] ERROR: {error_msg}")
            log_to_file(f"[Queue] Response preview: {response.text[:500]}")
            
            def _show_html_error():
                self._queue_status_label.config(text=f"❌ PHP returned HTML not JSON! Check logs")
            self._root.after(0, _show_html_error)
            
            raise Exception(error_msg)
        
        # Update UI to show we're parsing JSON
        def _update_status_parsing():
            self._queue_status_label.config(text=f"🔄 Parsing JSON response for job {job_id}...")
        self._root.after(0, _update_status_parsing)
        
        # Try to parse as JSON
        try:
            result = response.json()
            log_to_file(f"[Queue] ✓ Successfully parsed JSON response")
            log_to_file(f"[Queue] JSON keys: {list(result.keys()) if isinstance(result, dict) else 'not a dict'}")
            
            # Check if PHP returned an error in JSON
            if isinstance(result, dict) and result.get('ok') == False:
                error_details = result.get('status', {}).get('message', 'Unknown error')
                log_to_file(f"[Queue] PHP script returned error: {error_details}")
                
                def _show_php_error():
                    self._queue_status_label.config(text=f"❌ PHP Error: {error_details[:60]}")
                self._root.after(0, _show_php_error)
                
                raise Exception(f"PHP processing failed: {error_details}")
            
            # Check if PHP already saved the file (it does this before returning status)
            # The result contains the savePath where the actual listings JSON was saved
            if isinstance(result, dict) and 'status' in result:
                status_info = result.get('status', {})
                result_info = status_info.get('result', {})
                saved_path = result_info.get('savePath', '')
                listings_count = result_info.get('listingsCount', 0)
                
                log_to_file(f"[Queue] PHP saved listings to: {saved_path}")
                log_to_file(f"[Queue] Listings count: {listings_count}")
                
                # The JSON file should already exist with the actual data
                # Check if it exists and has the listings data
                html_filename = html_file.stem
                json_file = html_dir / f"{html_filename}.json"
                
                if json_file.exists():
                    # Read the existing file to verify it has listings data
                    try:
                        with open(json_file, 'r', encoding='utf-8') as f:
                            file_content = json.load(f)
                        
                        # Check if it's the job status (wrong) or listings array (correct)
                        if isinstance(file_content, dict) and 'ok' in file_content:
                            log_to_file(f"[Queue] File contains job status, not listings. Looking for actual data...")
                            # The PHP script should have saved the real data before uploading
                            # Let's check if there's a listings array somewhere
                            if saved_path and os.path.exists(saved_path):
                                log_to_file(f"[Queue] Loading actual listings from PHP-saved file: {saved_path}")
                                with open(saved_path, 'r', encoding='utf-8') as f:
                                    listings_data = json.load(f)
                                # Save the actual listings data to our expected location
                                result = listings_data
                            else:
                                log_to_file(f"[Queue] WARNING: PHP saved path not found, keeping job status")
                        else:
                            log_to_file(f"[Queue] ✓ File already contains listings data ({len(file_content) if isinstance(file_content, list) else 'unknown'} items)")
                            result = file_content
                    except Exception as read_err:
                        log_to_file(f"[Queue] Error reading existing JSON: {read_err}")
            
        except Exception as e:
            error_msg = f"Failed to parse JSON: {e}. Response preview: {response.text[:200]}"
            log_to_file(f"[Queue] ERROR: {error_msg}")
            
            def _show_parse_error():
                self._queue_status_label.config(text=f"❌ JSON Parse Error: {str(e)[:40]}")
            self._root.after(0, _show_parse_error)
            
            raise Exception(error_msg)
        
        # Save JSON result with same prefix as HTML file
        # Inject network_id into each listing for downstream steps
        def _inject_network_id(payload, nid: int):
            try:
                if isinstance(payload, list):
                    for item in payload:
                        if isinstance(item, dict):
                            item['network_id'] = nid
                    return payload
                if isinstance(payload, dict):
                    # Common containers: 'data' or 'listings'
                    if 'data' in payload and isinstance(payload['data'], list):
                        for item in payload['data']:
                            if isinstance(item, dict):
                                item['network_id'] = nid
                        return payload
                    if 'listings' in payload and isinstance(payload['listings'], list):
                        for item in payload['listings']:
                            if isinstance(item, dict):
                                item['network_id'] = nid
                        return payload
                    # Otherwise, if it's a listing-like dict
                    payload['network_id'] = nid
                    return payload
            except Exception as _inj:
                log_to_file(f"[Queue] Failed to inject network_id: {_inj}")
            return payload

        result = _inject_network_id(result, int(job_id))

        # Extract prefix from html_file (e.g., "networks" from "networks_4.html")
        html_filename = html_file.stem  # Gets filename without extension
        json_file = html_dir / f"{html_filename}.json"
        
        log_to_file(f"[Queue] ========== SAVING JSON ==========")
        log_to_file(f"[Queue] JSON file path: {json_file}")
        
        # Update UI to show we're saving
        def _update_status_saving():
            self._queue_status_label.config(text=f"💾 Saving listings JSON to {json_file.name}...")
        self._root.after(0, _update_status_saving)
        
        try:
            # Save the actual listings data (not the job status)
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2)
            
            log_to_file(f"[Queue] ✓✓✓ JSON SAVED SUCCESSFULLY")
            log_to_file(f"[Queue] File exists: {json_file.exists()}")
            log_to_file(f"[Queue] File size: {json_file.stat().st_size} bytes")
            
            # Count listings if it's an array
            listings_count = len(result) if isinstance(result, list) else 'unknown'
            log_to_file(f"[Queue] Listings in JSON: {listings_count}")
            
            # Update UI with success message showing file size and count
            file_size_kb = json_file.stat().st_size / 1024
            def _update_status_saved():
                self._queue_status_label.config(text=f"✅ Saved {listings_count} listings! {json_file.name} ({file_size_kb:.1f} KB)")
            self._root.after(0, _update_status_saved)
            
        except Exception as save_err:
            error_msg = f"Failed to save JSON file: {save_err}"
            log_to_file(f"[Queue] ERROR: {error_msg}")
            
            def _show_save_error():
                self._queue_status_label.config(text=f"❌ Save Error: {str(save_err)[:50]}")
            self._root.after(0, _show_save_error)
            
            raise Exception(error_msg)
        
        log_to_file(f"[Queue] ========== CREATE JSON END ==========")
        return str(json_file)
    
    def _step_manual_match(self, job_id, link):
        """Step 3: Download images - extracts and downloads all images from listings"""
        log_to_file(f"[Queue] ========== DOWNLOAD IMAGES START ==========")
        log_to_file(f"[Queue] Downloading images for job {job_id}")
        print(f"[3.IMAGE] Starting image download for job {job_id}")
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        html_dir = BASE_DIR / date_str
        
        # Find JSON file
        json_file = None
        for f in html_dir.glob(f"*_{job_id}.json"):
            json_file = f
            break
        
        if not json_file or not json_file.exists():
            raise Exception("JSON file not found - run Step 2 first")
        
        log_to_file(f"[Queue] Found JSON file: {json_file}")
        print(f"[3.IMAGE] JSON file: {json_file.name}")
        
        # Read the JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Handle different JSON structures
        if isinstance(json_data, list):
            listings = json_data
        elif isinstance(json_data, dict):
            if 'data' in json_data:
                listings = json_data['data']
            elif 'listings' in json_data:
                listings = json_data['listings']
            else:
                listings = [json_data]
        else:
            raise Exception(f"Unexpected JSON type: {type(json_data)}")
        
        total_listings = len(listings)
        log_to_file(f"[Queue] Found {total_listings} listings with images")
        print(f"[3.IMAGE] Found {total_listings} listings")
        
        def _update_status(msg):
            self._root.after(0, lambda: self._queue_status_label.config(text=msg))
        
        _update_status(f"📥 Downloading images from {total_listings} listings...")
        
        # Create images folder: networks_{job_id}
        images_dir = html_dir / f"networks_{job_id}"
        images_dir.mkdir(exist_ok=True)
        log_to_file(f"[Queue] Images folder: {images_dir}")
        print(f"[3.IMAGE] Output folder: {images_dir.name}")
        
        # Download images
        downloaded = 0
        skipped = 0
        failed = 0
        
        for idx, listing in enumerate(listings, 1):
            if not isinstance(listing, dict):
                continue
            
            listing_id = listing.get('listing_id', f'unknown_{idx}')
            img_urls = listing.get('img_urls', '')
            
            if not img_urls:
                skipped += 1
                continue
            
            # Parse URLs (can be comma-separated)
            if isinstance(img_urls, str):
                urls = [url.strip() for url in img_urls.split(',') if url.strip()]
            elif isinstance(img_urls, list):
                urls = img_urls
            else:
                urls = [str(img_urls)]
            
            log_to_file(f"[Queue] [{idx}/{total_listings}] Listing {listing_id}: {len(urls)} image(s)")
            
            # Download each image
            for img_idx, url in enumerate(urls, 1):
                try:
                    # Get file extension
                    parsed_url = urlparse(url)
                    ext = os.path.splitext(parsed_url.path)[1]
                    if not ext or ext.lower() not in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
                        ext = '.jpg'
                    
                    # Create unique filename
                    if len(urls) > 1:
                        filename = f"{listing_id}_{img_idx}{ext}"
                    else:
                        filename = f"{listing_id}{ext}"
                    
                    save_path = images_dir / filename
                    
                    # Skip if exists
                    if save_path.exists():
                        skipped += 1
                        continue
                    
                    # Download
                    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                    response = requests.get(url, headers=headers, timeout=30, stream=True)
                    response.raise_for_status()
                    
                    with open(save_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    
                    file_size = save_path.stat().st_size
                    log_to_file(f"[Queue] ✓ Downloaded: {filename} ({file_size:,} bytes)")
                    downloaded += 1
                    
                    # Update UI every 5 images
                    if downloaded % 5 == 0:
                        _update_status(f"📥 Downloaded {downloaded} images...")
                    
                    time.sleep(0.2)  # Small delay
                    
                except Exception as img_err:
                    log_to_file(f"[Queue] ✗ Failed to download {url}: {img_err}")
                    failed += 1
        
        log_to_file(f"[Queue] ========== DOWNLOAD IMAGES COMPLETE ==========")
        log_to_file(f"[Queue] Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")
        print(f"[3.IMAGE] ✅ Downloaded: {downloaded}, Skipped: {skipped}, Failed: {failed}")
        
        return f"✅ Downloaded {downloaded} images (skipped {skipped}, failed {failed})"
    
    def _step_process_db(self, job_id):
        """Step 4: Upload images to server with progress bar"""
        log_to_file(f"[Queue] ========== UPLOAD IMAGES TO SERVER START ==========")
        log_to_file(f"[Queue] Uploading images for job {job_id}")
        print(f"[4.DB] Starting image upload for job {job_id}")
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        html_dir = BASE_DIR / date_str
        
        # Find images folder created in Step 3
        images_dir = html_dir / f"networks_{job_id}"
        
        if not images_dir.exists():
            raise Exception("Images folder not found - run Step 3 first")
        
        # Get list of image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
            image_files.extend(list(images_dir.glob(ext)))
        
        total_images = len(image_files)
        
        if total_images == 0:
            raise Exception("No images found in folder - run Step 3 first")
        
        log_to_file(f"[Queue] Found {total_images} images to upload")
        print(f"[4.DB] Found {total_images} images to upload")
        
        # Create progress bar dialog
        progress_window = tk.Toplevel(self._root)
        progress_window.title(f"Uploading Images - Job {job_id}")
        progress_window.geometry("500x250")
        progress_window.configure(bg="#2C3E50")
        progress_window.transient(self._root)
        progress_window.grab_set()
        
        # Center the window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (250 // 2)
        progress_window.geometry(f"500x250+{x}+{y}")
        
        # Progress widgets
        tk.Label(progress_window, text=f"📤 Uploading {total_images} images to server", 
                 bg="#2C3E50", fg="#ECF0F1", font=("Segoe UI", 12, "bold")).pack(pady=10)
        
        progress_label = tk.Label(progress_window, text="Preparing...", 
                                  bg="#2C3E50", fg="#ECF0F1", font=("Segoe UI", 10))
        progress_label.pack(pady=5)
        
        # Progress bar
        progress_bar = ttk.Progressbar(progress_window, length=450, mode='determinate', maximum=total_images)
        progress_bar.pack(pady=10)
        
        time_label = tk.Label(progress_window, text="Estimating time...", 
                             bg="#2C3E50", fg="#95A5A6", font=("Segoe UI", 9))
        time_label.pack(pady=5)
        
        status_label = tk.Label(progress_window, text="", 
                               bg="#2C3E50", fg="#3498DB", font=("Segoe UI", 9))
        status_label.pack(pady=5)
        
        # Control variables for pause/resume
        paused = {"value": False}
        cancelled = {"value": False}
        
        # Button frame
        btn_frame = tk.Frame(progress_window, bg="#2C3E50")
        btn_frame.pack(pady=10)
        
        def toggle_pause():
            paused["value"] = not paused["value"]
            if paused["value"]:
                pause_btn.config(text="▶ Resume", bg="#27AE60")
                status_label.config(text="⏸ Paused", fg="#F39C12")
            else:
                pause_btn.config(text="⏸ Pause", bg="#F39C12")
                status_label.config(text="▶ Resuming...", fg="#3498DB")
        
        def cancel_upload():
            cancelled["value"] = True
            status_label.config(text="❌ Cancelling...", fg="#E74C3C")
        
        pause_btn = tk.Button(btn_frame, text="⏸ Pause", command=toggle_pause,
                             bg="#F39C12", fg="#fff", font=("Segoe UI", 9), 
                             relief="flat", padx=15, pady=5)
        pause_btn.pack(side="left", padx=5)
        
        cancel_btn = tk.Button(btn_frame, text="❌ Cancel", command=cancel_upload,
                              bg="#E74C3C", fg="#fff", font=("Segoe UI", 9),
                              relief="flat", padx=15, pady=5)
        cancel_btn.pack(side="left", padx=5)
        
        progress_window.update()
        
        # Upload images via SFTP
        remote_dir = f"/home/daniel/trustyhousing.com/app/public/img/thumbnails"
        
        uploaded = 0
        skipped = 0
        failed = 0
        start_time = time.time()
        
        try:
            # Connect to SFTP
            log_to_file(f"[Queue] Connecting to SFTP server {SFTP_HOST}:{SFTP_PORT}")
            transport, sftp = _sftp_connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS)
            
            # Create remote directory
            _sftp_ensure_dir(sftp, remote_dir)
            log_to_file(f"[Queue] Remote directory ready: {remote_dir}")
            
            # Get list of existing files on server to skip duplicates
            existing_files = set()
            try:
                existing_files = set(sftp.listdir(remote_dir))
                log_to_file(f"[Queue] Found {len(existing_files)} existing files on server")
            except Exception as list_err:
                log_to_file(f"[Queue] Could not list remote files (continuing anyway): {list_err}")
            
            for idx, image_file in enumerate(image_files, 1):
                # Check if cancelled
                if cancelled["value"]:
                    log_to_file(f"[Queue] Upload cancelled by user at {idx}/{total_images}")
                    progress_label.config(text=f"❌ Cancelled at {idx}/{total_images}")
                    status_label.config(text=f"Uploaded: {uploaded}, Failed: {failed}", fg="#E74C3C")
                    progress_window.update()
                    time.sleep(2)
                    progress_window.destroy()
                    raise Exception(f"Upload cancelled by user. Uploaded: {uploaded}/{total_images}")
                
                # Wait while paused
                while paused["value"]:
                    progress_window.update()
                    time.sleep(0.1)
                    if cancelled["value"]:
                        break
                
                try:
                    # Check if file already exists on server
                    if image_file.name in existing_files:
                        skipped += 1
                        log_to_file(f"[Queue] ⊘ Skipped (exists): {image_file.name}")
                        status_label.config(text=f"⊘ Skipped: {image_file.name} (already exists)", fg="#95A5A6")
                        progress_window.update()
                        continue
                    
                    # Update progress
                    progress_bar['value'] = idx - 1
                    progress_label.config(text=f"Uploading: {image_file.name} ({idx}/{total_images})")
                    
                    # Calculate estimated time
                    if idx > 1:
                        elapsed = time.time() - start_time
                        avg_time_per_image = elapsed / (idx - 1)
                        remaining_images = total_images - (idx - 1)
                        estimated_seconds = avg_time_per_image * remaining_images
                        
                        if estimated_seconds < 60:
                            eta_text = f"ETA: {int(estimated_seconds)}s"
                        elif estimated_seconds < 3600:
                            minutes = int(estimated_seconds / 60)
                            seconds = int(estimated_seconds % 60)
                            eta_text = f"ETA: {minutes}m {seconds}s"
                        else:
                            hours = int(estimated_seconds / 3600)
                            minutes = int((estimated_seconds % 3600) / 60)
                            eta_text = f"ETA: {hours}h {minutes}m"
                        
                        time_label.config(text=eta_text)
                    
                    progress_window.update()
                    
                    # Upload file
                    remote_path = f"{remote_dir}/{image_file.name}"
                    log_to_file(f"[Queue] Uploading: {image_file} -> {remote_path}")
                    sftp.put(str(image_file), remote_path)
                    
                    file_size = image_file.stat().st_size
                    uploaded += 1
                    
                    status_label.config(text=f"✓ {image_file.name} ({file_size:,} bytes)", fg="#2ECC71")
                    progress_window.update()
                    
                    log_to_file(f"[Queue] ✓ Uploaded [{idx}/{total_images}]: {image_file.name}")
                    
                    # Small delay
                    time.sleep(0.1)
                    
                except Exception as upload_err:
                    failed += 1
                    error_msg = str(upload_err)
                    status_label.config(text=f"✗ Failed: {image_file.name}", fg="#E74C3C")
                    log_to_file(f"[Queue] ✗ Upload failed: {image_file.name} - {error_msg}")
                    progress_window.update()
                    
                    # Stop upload on error and show detailed error
                    log_to_file(f"[Queue] Stopping upload due to error")
                    progress_label.config(text=f"❌ Upload failed at {idx}/{total_images}")
                    time_label.config(text=f"Error: {error_msg[:50]}")
                    
                    # Show error details in a larger label
                    error_detail = tk.Label(progress_window, 
                                           text=f"Error details: {error_msg[:100]}", 
                                           bg="#2C3E50", fg="#E74C3C", 
                                           font=("Segoe UI", 8),
                                           wraplength=450)
                    error_detail.pack(pady=5)
                    
                    progress_window.update()
                    time.sleep(5)  # Show error for 5 seconds
                    progress_window.destroy()
                    
                    # Close SFTP before raising
                    try:
                        sftp.close()
                        transport.close()
                    except:
                        pass
                    
                    raise Exception(f"Upload failed at {idx}/{total_images}: {error_msg}")
            
            # Close SFTP connection
            sftp.close()
            transport.close()
            
            # Final progress update
            progress_bar['value'] = total_images
            elapsed_total = time.time() - start_time
            
            if elapsed_total < 60:
                elapsed_text = f"{int(elapsed_total)}s"
            else:
                minutes = int(elapsed_total / 60)
                seconds = int(elapsed_total % 60)
                elapsed_text = f"{minutes}m {seconds}s"
            
            progress_label.config(text=f"✅ Upload complete!")
            time_label.config(text=f"Total time: {elapsed_text}")
            status_label.config(text=f"Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}", fg="#2ECC71")
            progress_window.update()
            
            log_to_file(f"[Queue] ========== UPLOAD IMAGES COMPLETE ==========")
            log_to_file(f"[Queue] Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}, Time: {elapsed_text}")
            print(f"[4.DB] ✅ Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}, Time: {elapsed_text}")
            
            # Wait 2 seconds before closing
            time.sleep(2)
            progress_window.destroy()
            
            return f"✅ Uploaded {uploaded} images in {elapsed_text} (skipped: {skipped}, failed: {failed})"
            
        except Exception as e:
            progress_window.destroy()
            log_to_file(f"[Queue] ✗ Upload error: {e}")
            log_exception("Upload images error")
            raise Exception(f"Upload failed: {str(e)}")
    
    def _step_process_db_with_progress(self, job_id, progress_callback):
        """Step 4: Upload images to server with progress callback (no popup window)"""
        log_to_file(f"[Queue] ========== UPLOAD IMAGES TO SERVER START (WITH CALLBACK) ==========")
        log_to_file(f"[Queue] Uploading images for job {job_id}")
        print(f"[4.DB] Starting image upload for job {job_id}")
        
        date_str = datetime.now().strftime("%Y-%m-%d")
        html_dir = BASE_DIR / date_str
        
        # Find images folder created in Step 3
        images_dir = html_dir / f"networks_{job_id}"
        
        if not images_dir.exists():
            raise Exception("Images folder not found - run Step 3 first")
        
        # Get list of image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
            image_files.extend(list(images_dir.glob(ext)))
        
        total_images = len(image_files)
        
        if total_images == 0:
            raise Exception("No images found in folder - run Step 3 first")
        
        log_to_file(f"[Queue] Found {total_images} images to upload")
        print(f"[4.DB] Found {total_images} images to upload")
        
        # Upload images via SFTP
        remote_dir = f"/home/daniel/trustyhousing.com/app/public/img/thumbnails"
        
        uploaded = 0
        skipped = 0
        failed = 0
        start_time = time.time()
        
        # Connect to SFTP
        log_to_file(f"[Queue] Connecting to SFTP server {SFTP_HOST}:{SFTP_PORT}")
        transport, sftp = _sftp_connect(SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS)
        
        # Create remote directory
        _sftp_ensure_dir(sftp, remote_dir)
        log_to_file(f"[Queue] Remote directory ready: {remote_dir}")
        
        # Get list of existing files on server to skip duplicates
        existing_files = set()
        try:
            existing_files = set(sftp.listdir(remote_dir))
            log_to_file(f"[Queue] Found {len(existing_files)} existing files on server")
        except Exception as list_err:
            log_to_file(f"[Queue] Could not list remote files (continuing anyway): {list_err}")
        
        for idx, image_file in enumerate(image_files, 1):
            try:
                filename = image_file.name
                
                # Check if file already exists on server
                if filename in existing_files:
                    skipped += 1
                    log_to_file(f"[Queue] ⊘ Skipped (exists): {filename}")
                    progress_callback(idx, total_images, filename, "skipped", "Already exists on server")
                    continue
                
                # Update progress - uploading
                progress_callback(idx, total_images, filename, "uploading", "Uploading...")
                
                # Upload file
                remote_path = f"{remote_dir}/{filename}"
                log_to_file(f"[Queue] Uploading: {image_file} -> {remote_path}")
                sftp.put(str(image_file), remote_path)
                
                file_size = image_file.stat().st_size
                uploaded += 1
                
                log_to_file(f"[Queue] ✓ Uploaded [{idx}/{total_images}]: {filename}")
                progress_callback(idx, total_images, filename, "uploaded", f"Uploaded ({file_size:,} bytes)")
                
                # Small delay
                time.sleep(0.1)
                
            except Exception as upload_err:
                failed += 1
                error_msg = str(upload_err)
                log_to_file(f"[Queue] ✗ Upload failed: {filename} - {error_msg}")
                progress_callback(idx, total_images, filename, "failed", error_msg)
                
                # Continue with next file instead of stopping
                continue
        
        # Close SFTP connection
        sftp.close()
        transport.close()
        
        elapsed_total = time.time() - start_time
        
        if elapsed_total < 60:
            elapsed_text = f"{int(elapsed_total)}s"
        else:
            minutes = int(elapsed_total / 60)
            seconds = int(elapsed_total % 60)
            elapsed_text = f"{minutes}m {seconds}s"
        
        log_to_file(f"[Queue] ========== UPLOAD IMAGES COMPLETE ==========")
        log_to_file(f"[Queue] Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}, Time: {elapsed_text}")
        print(f"[4.DB] ✅ Uploaded: {uploaded}, Skipped: {skipped}, Failed: {failed}, Time: {elapsed_text}")
        
        return f"✅ Uploaded {uploaded} images in {elapsed_text} (skipped: {skipped}, failed: {failed})"
    
    
    def _step_insert_db(self, job_id, table=None):
        """Step 5: Insert into DB - Show progress window with stats"""
        log_to_file(f"[Queue] Inserting into DB for job {job_id}")
        
        # Show insert progress window (pass table for status updates)
        try:
            show_insert_db_window(job_id, self._root, table)
        except TypeError:
            # Backward compatibility if function signature not updated
            show_insert_db_window(job_id, self._root)
        
        return "Database insert started"
    
    def _step_address_match(self, job_id):
        """Step 6: Address Match - Show addresses from JSON"""
        log_to_file(f"[Queue] Starting address match for job {job_id}")
        
        # Show address match window
        show_address_match_window(job_id, self._root)
        
        return "Address match window opened"

