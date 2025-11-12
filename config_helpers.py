#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Helper functions
Extracted from config_utils.py (lines 6673-9428)
"""

from config_core import *
from config_hud_api import hud_push
from config_auth import (
    BASE_DIR, CFG, LOG_PATH, TELEGRAM_ENABLED, TELEGRAM_BOT_TOKEN, 
    TELEGRAM_CHAT_ID, ERROR_NOTIFY_COOLDOWN_SEC
)

# Import ADDRESS_MATCH_CALLBACKS after config_hud is defined to avoid circular import
def get_address_match_callbacks():
    from config_hud import ADDRESS_MATCH_CALLBACKS
    return ADDRESS_MATCH_CALLBACKS

# Track open Address Match windows to prevent duplicates
_OPEN_ADDRESS_MATCH_WINDOWS = {}

def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)

def log_file(msg: str):
    try:
        ensure_dir(LOG_PATH.parent)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        LOG_PATH.write_text(
            (LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else "") \
            + f"[{stamp}] {msg}\n",
            encoding="utf-8"
        )
    except Exception:
        pass
    logging.info(msg)
    hud_push(msg)

# ----------------------------
# Parcel field extraction helper
# ----------------------------
def extract_parcel_fields(ocr_text: str) -> dict:
    """Extract structured fields from OCR text of parcel website.
    Customize patterns based on your specific parcel site layout.
    """
    fields = {}
    
    try:
        lines = [l.strip() for l in ocr_text.split('\n') if l.strip()]
        
        # Common parcel field patterns (customize for your site)
        patterns = {
            'parcel_number': [r'parcel\s*#?\s*:?\s*([A-Z0-9\-]+)', r'parcel\s+id\s*:?\s*([A-Z0-9\-]+)'],
            'owner': [r'owner\s*:?\s*(.+?)(?:\n|$)', r'property\s+owner\s*:?\s*(.+?)(?:\n|$)'],
            'address': [r'site\s+address\s*:?\s*(.+?)(?:\n|$)', r'property\s+address\s*:?\s*(.+?)(?:\n|$)'],
            'legal_description': [r'legal\s+desc(?:ription)?\s*:?\s*(.+?)(?:\n|$)'],
            'acres': [r'acres\s*:?\s*([\d.]+)', r'area\s*:?\s*([\d.]+)\s*ac'],
            'assessed_value': [r'assessed\s+value\s*:?\s*\$?([\d,]+)', r'total\s+value\s*:?\s*\$?([\d,]+)'],
            'year_built': [r'year\s+built\s*:?\s*(\d{4})', r'built\s*:?\s*(\d{4})'],
            'building_sqft': [r'building\s+area\s*:?\s*([\d,]+)\s*sq', r'sqft\s*:?\s*([\d,]+)'],
            'zoning': [r'zoning\s*:?\s*([A-Z0-9\-]+)', r'zone\s*:?\s*([A-Z0-9\-]+)'],
        }
        
        for field, regexes in patterns.items():
            for regex in regexes:
                match = re.search(regex, ocr_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    fields[field] = match.group(1).strip()
                    break
        
        # Try to extract any table-like data
        table_data = []
        for i, line in enumerate(lines):
            if any(kw in line.lower() for kw in ['parcel', 'owner', 'address', 'value', 'tax']):
                table_data.append(line)
        
        if table_data:
            fields['raw_data'] = table_data
            
    except Exception as e:
        fields['extraction_error'] = str(e)
    
    return fields

# ----------------------------
# Manual assist: open browser
# ----------------------------
def launch_manual_browser(url: str):
    """Open Chrome if available, otherwise default browser. Non-blocking.
    Intended to help manual inspection when parser returns 0 listings.
    """
    try:
        hud_push(f"Opening Chrome for manual inspect …")
        logging.info(f"Opening browser for manual inspect: {url}")

        # Try common Chrome paths on Windows
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ]

        # macOS and Linux fallbacks
        if sys.platform == "darwin":
            # Use 'open -a Google Chrome' if available
            try:
                subprocess.Popen(["/usr/bin/open", "-a", "Google Chrome", url],
                                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass
        elif sys.platform.startswith("linux"):
            for bin_name in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
                candidates.append(bin_name)

        # Attempt Windows/Linux candidates
        for p in candidates:
            try:
                if os.path.isabs(p) and os.path.isfile(p):
                    subprocess.Popen([p, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
                # If it's a bare command (Linux), try spawning it directly
                if not os.path.isabs(p):
                    subprocess.Popen([p, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
            except Exception:
                continue

        # Fallback to default browser
        webbrowser.open_new_tab(url)
    except Exception as _e:
        # Last-resort: ignore opening errors, but note in HUD
        hud_push("[WARN] Could not open browser for manual inspect")

# ----------------------------
# Manual assist: open browser docked right (Windows)
# ----------------------------
def launch_manual_browser_docked_right(url: str, left_ratio: float = 0.25):
    """Open Chrome in a new window positioned at X=left_ratio*screen_width, Y=0,
    size=(screen_width-X) x screen_height. Falls back to default open.
    """
    try:
        import ctypes
        # Get screen size on Windows
        user32 = ctypes.windll.user32 if hasattr(ctypes, 'windll') else None
        if user32:
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
        else:
            screen_w, screen_h = 1920, 1080
        x = max(int(screen_w * left_ratio), 0)
        y = 0
        w = max(screen_w - x, 800)
        h = screen_h

        # Try common Chrome paths on Windows with window placement flags
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ]
        args = ["--new-window", f"--window-position={x},{y}", f"--window-size={w},{h}"]
        for p in candidates:
            try:
                if os.path.isabs(p) and os.path.isfile(p):
                    subprocess.Popen([p, *args, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return
            except Exception:
                continue
        # Fallbacks: default behavior
        launch_manual_browser(url)
    except Exception:
        launch_manual_browser(url)

def launch_manual_browser_docked_left(url: str, left_offset_ratio: float = 0.20, width_ratio: float = 0.80, zoom_percent: float = 25.0, auto_open_devtools: bool = True):
    """Open Chrome in a new window positioned at specified offset from left, with specified width and zoom level.
    Optionally auto-opens DevTools. Falls back to default open. Used for manual CSS selector capture.
    Default: 20% from left, 80% width, 25% zoom
    """
    try:
        import ctypes
        import logging
        # Get screen size on Windows
        user32 = ctypes.windll.user32 if hasattr(ctypes, 'windll') else None
        if user32:
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
        else:
            screen_w, screen_h = 1920, 1080
        # Calculate window width first
        w = int(screen_w * width_ratio)
        h = screen_h
        
        logging.info(f"[Chrome] Screen size: {screen_w}x{screen_h}")
        logging.info(f"[Chrome] Zoom level: {zoom_percent}%")

        # Try common Chrome paths on Windows with window placement flags
        candidates = [
            os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        ]
        # Add zoom level: --force-device-scale-factor for zoom (0.25 = 25%)
        zoom_factor = zoom_percent / 100.0
        
        # Don't use --auto-open-devtools-for-tabs as it conflicts with window sizing
        # We'll open DevTools manually with F12 hotkey after Chrome opens
        # Use temp profile to prevent Chrome from restoring previous window size
        import tempfile
        temp_profile = tempfile.mkdtemp(prefix="chrome_403_")
        
        # Using --force-device-scale-factor to set zoom level
        # This affects BOTH content zoom AND window size, so we compensate
        zoom_factor = 0.40  # 40% zoom
        # Compensate window size for zoom factor
        w_adjusted = int(w / zoom_factor)
        h_adjusted = int(h / zoom_factor)
        
        # Position at RIGHT side of screen
        # Both position AND size are affected by zoom factor
        x_adjusted = int((screen_w - w) / zoom_factor)
        y = 0
        
        logging.info(f"[Chrome] Window position (adjusted): x={x_adjusted}, y={y}")
        logging.info(f"[Chrome] Window size (adjusted): {w_adjusted}x{h_adjusted}")
        logging.info(f"[Chrome] Will display at right side with 80% screen width at 25% zoom")
        
        args = [
            "--new-window",
            f"--user-data-dir={temp_profile}",  # Temp profile to prevent size restoration
            "--no-first-run",  # Disable first run experience
            "--no-default-browser-check",  # Don't check if Chrome is default
            "--disable-features=Translate",  # Disable translate bar to avoid popup
            "--disable-session-crashed-bubble",  # Don't show "Chrome didn't shut down correctly"
            "--disable-infobars",  # Disable infobars
            "--disable-sync",  # Disable sync splash screen
            f"--force-device-scale-factor={zoom_factor}",  # Set zoom to 25%
            f"--window-position={x_adjusted},{y}",
            f"--window-size={w_adjusted},{h_adjusted}"  # Adjusted for zoom factor
        ]
        
        logging.info(f"[Chrome] Attempting to launch Chrome with args: {args}")
        for p in candidates:
            try:
                if os.path.isabs(p) and os.path.isfile(p):
                    logging.info(f"[Chrome] Launching Chrome from: {p}")
                    subprocess.Popen([p, *args, url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    logging.info(f"[Chrome] ✓ Chrome launched successfully")
                    return
            except Exception as e:
                logging.warning(f"[Chrome] Failed to launch from {p}: {e}")
                continue
        # Fallbacks: default behavior
        logging.warning(f"[Chrome] Chrome not found, falling back to default browser")
        launch_manual_browser(url)
    except Exception as e:
        logging.error(f"[Chrome] Error in launch_manual_browser_docked_left: {e}")
        launch_manual_browser(url)

def send_hotkeys_to_chrome(css_selector: str):
    """Send hotkeys to Chrome to help navigate to and copy an element with the given CSS selector.
    Uses pyautogui to automate keyboard interactions.
    """
    try:
        import pyautogui
        import time
        
        # Wait for Chrome to be ready
        time.sleep(2)
        
        # Press F12 to open DevTools (backup in case auto-open didn't work)
        pyautogui.press('f12')
        time.sleep(1)
        
        # Press Ctrl+Shift+C to enter element picker mode
        pyautogui.hotkey('ctrl', 'shift', 'c')
        time.sleep(0.5)
        
        return True
    except ImportError:
        # pyautogui not available
        return False
    except Exception as e:
        logging.warning(f"Failed to send hotkeys to Chrome: {e}")
        return False

# ----------------------------
# HTTP (no UI)
# ----------------------------
def http_get(url: str, timeout: float) -> str:
    r = requests.get(url, timeout=timeout, headers={"User-Agent": CFG["HTTP_UA"]})
    r.raise_for_status()
    return r.text

# ----------------------------
# Telegram helpers
# ----------------------------
def _send_telegram_text(message: str, parse_mode: str = "HTML") -> Optional[str]:
    if not TELEGRAM_ENABLED:
        return None
    try:
        api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": parse_mode, "disable_web_page_preview": True}
        resp = requests.post(api_url, data=payload, timeout=20)
        return resp.text
    except Exception as e:
        log_file(f"Telegram send failed: {e}")
        return None

def notify_telegram_error(title: str, details: Optional[str] = None, context: Optional[str] = None, throttle: bool = True):
    global _last_error_notif_ts
    now = time.time()
    if throttle and (now - _last_error_notif_ts) < ERROR_NOTIFY_COOLDOWN_SEC:
        return
    _last_error_notif_ts = now
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts = [f"🚨 <b>{title}</b>", f"<i>{ts}</i>"]
    if context:
        parts.append(f"<code>{context}</code>")
    if details:
        short = details if len(details) < 1500 else (details[:1500] + " …[truncated]")
        parts.append(f"<pre>{short}</pre>")
    msg = "\n".join(parts)
    _send_telegram_text(msg, parse_mode="HTML")
    hud_push(f"[ERR] {title} — {context or ''}")

# ----------------------------
# SFTP Upload (file/dir)
# ----------------------------
SFTP_HOST = os.getenv("SFTP_HOST", "172.104.206.182")
SFTP_PORT = int(os.getenv("SFTP_PORT", "23655"))
SFTP_USER = os.getenv("SFTP_USER", "daniel")
SFTP_PASS = os.getenv("SFTP_PASS", "Driver89*")
SFTP_ENABLED = os.getenv("SFTP_ENABLED", "1") in ("1", "true", "True")

def _sftp_connect(host: str, port: int, user: str, password: str):
    transport = paramiko.Transport((host, port))
    transport.connect(username=user, password=password)
    sftp = paramiko.SFTPClient.from_transport(transport)
    return transport, sftp

def _sftp_ensure_dir(sftp: paramiko.SFTPClient, remote_dir: str):
    """Ensure remote directory exists, creating all parent directories if needed"""
    parts = remote_dir.strip("/").split("/")
    cur = ""
    for part in parts:
        cur = f"{cur}/{part}" if cur else f"/{part}"
        try:
            sftp.stat(cur)
            log_to_file(f"[SFTP] Directory exists: {cur}")
        except FileNotFoundError:
            try:
                sftp.mkdir(cur)
                log_to_file(f"[SFTP] Created directory: {cur}")
            except Exception as mkdir_err:
                log_to_file(f"[SFTP] Failed to create directory {cur}: {mkdir_err}")
                # Try to continue anyway in case it's a permissions issue but dir exists

def sftp_upload_file(local_path: Path, host: str, port: int, user: str, password: str, remote_dir: str, remote_name: Optional[str] = None) -> bool:
    if not SFTP_ENABLED:
        log_file("SFTP disabled; skipping file upload.")
        return False
    try:
        transport, sftp = _sftp_connect(host, port, user, password)
        _sftp_ensure_dir(sftp, remote_dir)
        rname = remote_name if remote_name else local_path.name
        remote_path = f"{remote_dir.rstrip('/')}/{rname}"
        sftp.put(str(local_path), remote_path)
        sftp.close(); transport.close()
        log_file(f"SFTP upload OK: {local_path} -> {remote_path}")
        hud_push(f"↑ JSON uploaded: {rname}")
        return True
    except Exception as e:
        log_file(f"SFTP upload FAILED ({local_path}): {e}")
        notify_telegram_error(title="SFTP file upload failed", details=str(e), context=f"local={local_path} remote_dir={remote_dir}")
        return False

def sftp_upload_dir(local_dir: Path, host: str, port: int, user: str, password: str, remote_dir: str, remote_subdir: Optional[str] = None) -> bool:
    if not SFTP_ENABLED:
        log_file("SFTP disabled; skipping dir upload.")
        return False
    try:
        transport, sftp = _sftp_connect(host, port, user, password)
        # If remote_subdir is provided, upload into that fixed directory name under remote_dir;
        # otherwise, mirror the local directory name under the remote_dir.
        target_root = f"{remote_dir.rstrip('/')}/{remote_subdir or local_dir.name}"
        _sftp_ensure_dir(sftp, target_root)

        import os
        for root, dirs, files in os.walk(local_dir):
            rel = os.path.relpath(root, local_dir)
            remote_sub = target_root if rel == "." else f"{target_root}/{rel.replace('\\', '/')}"
            _sftp_ensure_dir(sftp, remote_sub)
            for fname in files:
                lpath = Path(root) / fname
                rpath = f"{remote_sub}/{fname}"
                try:
                    sftp.put(str(lpath), rpath)
                except Exception as e:
                    log_file(f"SFTP put failed: {lpath} -> {rpath}: {e}")

        sftp.close(); transport.close()
        log_file(f"SFTP folder upload OK: {local_dir} -> {target_root}")
        hud_push(f"↑ Images folder uploaded: {remote_subdir or local_dir.name}")
        return True
    except Exception as e:
        log_file(f"SFTP folder upload FAILED ({local_dir}): {e}")
        notify_telegram_error(title="SFTP folder upload failed", details=str(e), context=f"local_dir={local_dir} remote_dir={remote_dir}")
        return False

# ----------------------------
# Shared helpers for other modules
# ----------------------------
def save_global_json(path: Path, data: Dict[str, Any]):
    try:
        data["last_updated"] = datetime.now().isoformat(timespec="seconds")
        ensure_dir(path.parent)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log_file(f"Failed to save global JSON: {e}")
        notify_telegram_error(title="Save global JSON failed", details=str(e), context=str(path))

def load_global_json(path: Path) -> Dict[str, Any]:
    def _empty() -> Dict[str, Any]:
        return {"last_updated": None, "sources": {}}
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        log_file(f"Failed to load global JSON: {e}")
        notify_telegram_error(title="Load global JSON failed", details=str(e), context=str(path))
    return _empty()

def sanitize_ext(url: str, content_type: Optional[str]) -> str:
    if content_type:
        ct = content_type.split(";")[0].strip().lower()
        ext = guess_extension(ct)
        if ext:
            if ext == ".jpe": return ".jpg"
            return ext
        if ct == "image/jpg": return ".jpg"
        if ct == "image/webp": return ".webp"
        if ct == "image/png": return ".png"
        if ct == "image/jpeg": return ".jpg"
        if ct == "image/gif": return ".gif"
    path = urlparse(url).path.lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"

# ----------------------------
# Step 5: Address Match - Show addresses from JSON
# ----------------------------
def show_address_match_window(job_id, parent=None, manual_open=False):
    """Show a compact window with all addresses from the JSON for address matching.
    
    Args:
        job_id: The job ID to match addresses for
        parent: Parent window
        manual_open: If True, window was opened manually via link (don't auto-close on completion)
    """
    global _OPEN_ADDRESS_MATCH_WINDOWS  # Declare global at the very top
    
    from tkinter import messagebox
    import json
    
    log_to_file(f"[Address Match] Function called for job {job_id}, manual_open={manual_open}")
    
    # Check if window already exists for this job_id
    if job_id in _OPEN_ADDRESS_MATCH_WINDOWS:
        existing_window = _OPEN_ADDRESS_MATCH_WINDOWS[job_id]
        try:
            # Check if window still exists
            if existing_window.winfo_exists():
                log_to_file(f"[Address Match] ⚠️ Window for job {job_id} already exists - bringing to front instead of opening new window")
                existing_window.lift()
                existing_window.focus_force()
                return
            else:
                # Window was closed, remove from tracker
                log_to_file(f"[Address Match] Window was closed, removing from tracker")
                del _OPEN_ADDRESS_MATCH_WINDOWS[job_id]
        except Exception as e:
            # Window is invalid, remove from tracker
            log_to_file(f"[Address Match] Window is invalid ({e}), removing from tracker")
            del _OPEN_ADDRESS_MATCH_WINDOWS[job_id]
    
    try:
        import mysql.connector
        log_to_file(f"[Address Match] mysql.connector imported")
    except ImportError:
        log_to_file(f"[Address Match] mysql-connector-python is not installed")
        messagebox.showerror("Error", "mysql-connector-python is not installed", parent=parent)
        return
    
    # Create a shared DB connection helper to avoid creating connections for every query
    _db_pool = {"conn": None}
    
    def get_db_connection():
        """Get or create a shared DB connection for this window session."""
        if _db_pool["conn"] is None or not _db_pool["conn"].is_connected():
            try:
                _db_pool["conn"] = mysql.connector.connect(
                    host=CFG["MYSQL_HOST"],
                    user=CFG["MYSQL_USER"],
                    password=CFG["MYSQL_PASSWORD"],
                    database=CFG.get("MYSQL_DB", "offta"),
                    port=int(CFG.get("MYSQL_PORT", 3306)),
                    connection_timeout=10,
                    use_pure=True,
                    autocommit=True  # Auto-commit for simpler transaction handling
                )
            except Exception as e:
                log_to_file(f"[Address Match] DB connection failed: {e}")
                return None
        return _db_pool["conn"]
    
    def close_db_connection():
        """Close the shared DB connection when window closes."""
        if _db_pool["conn"] is not None:
            try:
                _db_pool["conn"].close()
            except Exception:
                pass
            _db_pool["conn"] = None
    
    # Find JSON file for this job - check both Networks and Websites subfolders
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Try Networks folder first (networks_X.json)
    json_path = BASE_DIR / date_str / "Networks" / f"networks_{job_id}.json"
    log_to_file(f"[Address Match] Looking for JSON at: {json_path}")
    
    # If not found, try Websites folder (google_places_X.json)
    if not json_path.exists():
        json_path = BASE_DIR / date_str / "Websites" / f"google_places_{job_id}.json"
        log_to_file(f"[Address Match] Not in Networks, trying Websites: {json_path}")
    
    # Search all date folders if not found today
    if not json_path.exists():
        log_to_file(f"[Address Match] JSON not found at expected path, searching...")
        # Search both Networks and Websites folders
        pattern1 = str(BASE_DIR / "*" / "Networks" / f"networks_{job_id}.json")
        pattern2 = str(BASE_DIR / "*" / "Websites" / f"google_places_{job_id}.json")
        matching = __import__('glob').glob(pattern1) + __import__('glob').glob(pattern2)
        if matching:
            json_path = Path(max(matching, key=lambda p: os.path.getmtime(p)))
            log_to_file(f"[Address Match] Found JSON at: {json_path}")
        else:
            log_to_file(f"[Address Match] No JSON file found for job {job_id}")
            messagebox.showerror("Error", f"No JSON file found for job {job_id}", parent=parent)
            return
    else:
        log_to_file(f"[Address Match] JSON found at expected path")
    
    # Load JSON
    try:
        log_to_file(f"[Address Match] Loading JSON...")
        with open(json_path, "r", encoding="utf-8") as f:
            listings = json.load(f)
        log_to_file(f"[Address Match] Loaded {len(listings)} listings")
    except Exception as e:
        log_to_file(f"[Address Match] Failed to load JSON: {e}")
        messagebox.showerror("Error", f"Failed to load JSON: {e}", parent=parent)
        return
    
    # Create compact window
    log_to_file(f"[Address Match] Creating window...")
    window = tk.Toplevel(parent)
    window.title(f"Address Match - Job {job_id}")
    log_to_file(f"[Address Match] Window created")
    window.configure(bg="#1E1E1E")
    
    # Add window to tracker
    _OPEN_ADDRESS_MATCH_WINDOWS[job_id] = window
    
    # Register cleanup when window is closed
    def on_window_close():
        """Clean up resources when window is closed."""
        close_db_connection()
        global _OPEN_ADDRESS_MATCH_WINDOWS
        if job_id in _OPEN_ADDRESS_MATCH_WINDOWS:
            del _OPEN_ADDRESS_MATCH_WINDOWS[job_id]
        log_to_file(f"[Address Match] Window for job {job_id} closed and removed from tracker")
        window.destroy()
    
    window.protocol("WM_DELETE_WINDOW", on_window_close)
    
    # Make window visible and focused (but not always on top)
    window.lift()
    window.focus_force()
    
    # Position window: next to Activity window (which is 20% of screen width)
    window.update_idletasks()  # Ensure geometry is calculated
    
    # Get screen dimensions
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    
    # Set window size (75% of screen width to leave room for Activity window)
    win_width = int(screen_width * 0.75)
    win_height = screen_height  # Full height
    
    # Position: right after Activity window (20% from left)
    x_pos = int(screen_width * 0.20)
    y_pos = 0
    
    # Ensure window doesn't go off-screen
    x_pos = max(0, x_pos)
    y_pos = max(0, y_pos)
    
    # Apply geometry
    window.geometry(f"{win_width}x{win_height}+{x_pos}+{y_pos}")

    # Pre-fill rest of fields if GA ID is present
    # If listings is a list of dicts, treat as addresses
    addresses = listings if isinstance(listings, list) else []
    for addr in addresses:
        if addr.get('ga_id'):
            # Pre-fill from preloaded GA record
            ga_data = addr.get('ga_data', {})
            if ga_data:
                addr['formatted_address'] = ga_data.get('formatted_address', addr.get('formatted_address', ''))
                addr['name'] = ga_data.get('name', addr.get('name', ''))
                addr['rating'] = ga_data.get('rating', addr.get('rating', ''))
                addr['user_ratings_total'] = ga_data.get('user_ratings_total', addr.get('user_ratings_total', ''))
            else:
                # Fallback: use existing fields if present
                addr['formatted_address'] = addr.get('formatted_address', '')
                addr['name'] = addr.get('name', '')
                addr['rating'] = addr.get('rating', '')
                addr['user_ratings_total'] = addr.get('user_ratings_total', '')

    # Header with live API call counter
    api_calls_count = tk.IntVar(master=window, value=0)
    # Track only NEW API calls made this session (not cached)
    new_api_calls_count = tk.IntVar(master=window, value=0)
    header_text_var = tk.StringVar(master=window, value=f"📍 Address Match ({len(listings)} listings • API calls: 0)")

    def update_header_text():
        try:
            header_text_var.set(f"📍 Address Match ({len(listings)} listings • API calls: {api_calls_count.get()})")
        except Exception as e:
            log_to_file(f"[Address Match] update_header_text error: {e}")

    def refresh_api_calls_tally():
        """Recompute API calls as the count of rows with GAPI != '-' and GAPI != empty."""
        try:
            count = 0
            for row_id in tree.get_children():
                try:
                    val = tree.set(row_id, "GAPI")
                    if val and val != "-" and val.strip():
                        count += 1
                except Exception:
                    continue
            api_calls_count.set(count)
            update_header_text()
        except Exception as e:
            log_to_file(f"[Address Match] refresh_api_calls_tally error: {e}")

    header_label = tk.Label(window, textvariable=header_text_var,
             bg="#1E1E1E", fg="#ECF0F1", font=("Segoe UI", 11, "bold"))
    header_label.pack(pady=5)

    # API usage stats label (today / week / month), updated from backend responses
    api_usage_var = tk.StringVar(master=window, value="API usage: today 0 • week 0 • month 0")
    api_usage_label = tk.Label(window, textvariable=api_usage_var,
             bg="#1E1E1E", fg="#95A5A6", font=("Segoe UI", 9))
    api_usage_label.pack(pady=(0,4))
    
    # Statistics and Filters Frame
    stats_frame = tk.Frame(window, bg="#1E1E1E")
    stats_frame.pack(fill="x", padx=10, pady=(0, 5))
    
    # Statistics labels
    stats_apt_id_var = tk.StringVar(master=window, value="Apt ID: 0")
    stats_pregaid_var = tk.StringVar(master=window, value="PreGAID: 0")
    stats_total_var = tk.StringVar(master=window, value="Total: 0")
    
    tk.Label(stats_frame, textvariable=stats_total_var, bg="#1E1E1E", fg="#ECF0F1", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
    tk.Label(stats_frame, textvariable=stats_apt_id_var, bg="#1E1E1E", fg="#3498DB", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
    tk.Label(stats_frame, textvariable=stats_pregaid_var, bg="#1E1E1E", fg="#2ECC71", font=("Segoe UI", 9)).pack(side="left", padx=(0, 15))
    
    # Master list of all row IDs (attached or detached)
    all_row_ids = []

    # Filter checkboxes
    filter_has_apt_id_var = tk.BooleanVar(master=window, value=True)
    filter_no_apt_id_var = tk.BooleanVar(master=window, value=False)
    filter_has_pregaid_var = tk.BooleanVar(master=window, value=True)
    filter_no_pregaid_var = tk.BooleanVar(master=window, value=True)

    def recompute_row_visibility():
        """Apply search + checkbox filters over ALL rows (attached or detached)."""
        try:
            query = search_var.get().lower().strip()
        except Exception:
            query = ""

        # Determine active filters
        fh_apt = bool(filter_has_apt_id_var.get())
        fn_apt = bool(filter_no_apt_id_var.get())
        fh_pre = bool(filter_has_pregaid_var.get())
        fn_pre = bool(filter_no_pregaid_var.get())

        # Reattach in original insertion order using position index
        pos = 0
        for rid in list(all_row_ids):
            try:
                apt_id = tree.set(rid, "Apt ID")
                pregaid = tree.set(rid, "PreGAID")
                values = tree.item(rid, "values")

                has_apt = apt_id not in ("", "-")
                has_pre = pregaid not in ("", "-")

                # Checkbox logic: row is allowed if it matches any selected option per category
                allow_apt = (has_apt and fh_apt) or ((not has_apt) and fn_apt)
                allow_pre = (has_pre and fh_pre) or ((not has_pre) and fn_pre)

                # Search filter
                allow_search = True
                if query:
                    allow_search = any(query in str(v).lower() for v in (values or []))

                show = allow_apt and allow_pre and allow_search
                if show:
                    tree.reattach(rid, '', pos)
                    pos += 1
                else:
                    tree.detach(rid)
            except Exception:
                # If we can't access a row, skip it
                pass
    
    tk.Label(stats_frame, text="Show:", bg="#1E1E1E", fg="#95A5A6", font=("Segoe UI", 9)).pack(side="left", padx=(0, 5))
    
    tk.Checkbutton(
        stats_frame, text="Has Apt ID", variable=filter_has_apt_id_var, command=recompute_row_visibility,
        bg="#1E1E1E", fg="#ECF0F1", selectcolor="#2C3E50", font=("Segoe UI", 9),
        activebackground="#1E1E1E", activeforeground="#3498DB"
    ).pack(side="left", padx=2)
    
    tk.Checkbutton(
        stats_frame, text="No Apt ID", variable=filter_no_apt_id_var, command=recompute_row_visibility,
        bg="#1E1E1E", fg="#ECF0F1", selectcolor="#2C3E50", font=("Segoe UI", 9),
        activebackground="#1E1E1E", activeforeground="#3498DB"
    ).pack(side="left", padx=2)
    
    tk.Checkbutton(
        stats_frame, text="Has PreGAID", variable=filter_has_pregaid_var, command=recompute_row_visibility,
        bg="#1E1E1E", fg="#ECF0F1", selectcolor="#2C3E50", font=("Segoe UI", 9),
        activebackground="#1E1E1E", activeforeground="#2ECC71"
    ).pack(side="left", padx=2)
    
    tk.Checkbutton(
        stats_frame, text="No PreGAID", variable=filter_no_pregaid_var, command=recompute_row_visibility,
        bg="#1E1E1E", fg="#ECF0F1", selectcolor="#2C3E50", font=("Segoe UI", 9),
        activebackground="#1E1E1E", activeforeground="#2ECC71"
    ).pack(side="left", padx=2)
    
    def update_statistics():
        """Calculate and update statistics over ALL rows (not just visible)."""
        total = len(all_row_ids)
        has_apt_id = 0
        has_pregaid = 0
        for rid in list(all_row_ids):
            try:
                apt_id = tree.set(rid, "Apt ID")
                pregaid = tree.set(rid, "PreGAID")
                if apt_id not in ("", "-"):
                    has_apt_id += 1
                if pregaid not in ("", "-"):
                    has_pregaid += 1
            except Exception:
                pass
        stats_total_var.set(f"Total: {total}")
        stats_apt_id_var.set(f"Apt ID: {has_apt_id}/{total}")
        stats_pregaid_var.set(f"PreGAID: {has_pregaid}/{total}")
        
        # Auto-close window if all PreGAIDs are filled AND window was opened automatically
        if total > 0 and has_pregaid == total and not manual_open:
            log_to_file(f"[Address Match] All {total} PreGAIDs filled! Window opened automatically - auto-closing and marking job as done...")
            
            # Trigger callback to notify Step 6 completion
            try:
                ADDRESS_MATCH_CALLBACKS = get_address_match_callbacks()
                cb = ADDRESS_MATCH_CALLBACKS.get(str(job_id)) or ADDRESS_MATCH_CALLBACKS.get(job_id)
                if cb:
                    # Get new API calls count
                    new_api_calls = api_calls_count.get()
                    log_to_file(f"[Address Match] Calling completion callback with {new_api_calls} API calls")
                    cb(new_api_calls)
                    # Remove callback after use
                    ADDRESS_MATCH_CALLBACKS.pop(str(job_id), None)
                    ADDRESS_MATCH_CALLBACKS.pop(job_id, None)
                else:
                    log_to_file(f"[Address Match] No callback registered for job {job_id}")
            except Exception as cb_err:
                log_to_file(f"[Address Match] Callback error: {cb_err}")
            
            # Mark job as done in database
            try:
                import mysql.connector
                from datetime import datetime
                conn = mysql.connector.connect(
                    host=CFG.get("MYSQL_HOST", "127.0.0.1"),
                    user=CFG.get("MYSQL_USER", "local_uzr"),
                    password=CFG.get("MYSQL_PASSWORD", "fuck"),
                    database=CFG.get("MYSQL_DB", "offta"),
                    port=int(CFG.get("MYSQL_PORT", 3306)),
                    connection_timeout=10
                )
                cursor = conn.cursor()
                
                # Update using id (job_id is the queue_websites.id)
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute("""
                    UPDATE queue_websites 
                    SET processed_at = %s, updated_at = %s, status = 'done'
                    WHERE id = %s
                """, (now_str, now_str, job_id))
                
                rows_updated = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
                
                if rows_updated > 0:
                    log_to_file(f"[Address Match] Updated queue_websites id={job_id} to 'done' with timestamps")
                else:
                    log_to_file(f"[Address Match] No queue_websites rows found with id={job_id}")
            except Exception as db_err:
                log_to_file(f"[Address Match] Failed to update status/timestamps: {db_err}")
            
            # Close the window after a short delay so user can see the completion
            window.after(1500, window.destroy)
        elif total > 0 and has_pregaid == total and manual_open:
            log_to_file(f"[Address Match] All {total} PreGAIDs filled, but window opened manually - keeping window open")
    
    # Search Bar (filters table in real-time)
    search_var = tk.StringVar()
    search_frame = tk.Frame(window, bg="#1E1E1E")
    search_frame.pack(fill="x", padx=10, pady=(0, 5))
    tk.Label(search_frame, text="🔍 Search:", bg="#1E1E1E", fg="#ECF0F1", font=("Segoe UI", 10)).pack(side="left")
    search_entry = tk.Entry(search_frame, textvariable=search_var, font=("Consolas", 10), bg="#2C3E50", fg="#ECF0F1", insertbackground="#ECF0F1")
    search_entry.pack(side="left", padx=(6, 0), fill="x", expand=True)
    
    # Table frame with scrollbars (vertical + horizontal)
    table_frame = tk.Frame(window, bg="#1E1E1E")
    table_frame.pack(fill="both", expand=True, padx=10, pady=5)
    
    # Create Treeview
    cols = ("#", "Apt ID", "PreGAID", "Google", "Formatted", "Name", "Rating", "Reviews", "GAID", "GPID", "KC_ID", "Score", "Type", "GAPI", "✓")
    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
    # Configure row tags for alternating colors and states
    try:
        tree.tag_configure("even", background="#FFFFFF")           # white
        tree.tag_configure("odd", background="#E6F7FF")            # light blue
        tree.tag_configure("error", background="#FFCCCC")          # light red
        tree.tag_configure("nomatch", background="#FFE6B3")        # light orange
    except Exception:
        pass
    
    tree.heading("#", text="#")
    tree.heading("Apt ID", text="Apt ID")
    tree.heading("PreGAID", text="PreGAID")
    tree.heading("Google", text="Google Address")
    tree.heading("Formatted", text="Formatted Address")
    tree.heading("Name", text="Name")
    tree.heading("Rating", text="Rating")
    tree.heading("Reviews", text="Reviews")
    tree.heading("GAID", text="GAID")
    tree.heading("GPID", text="GPID")
    tree.heading("KC_ID", text="KC_ID")
    tree.heading("Score", text="Score")
    tree.heading("Type", text="Type")
    tree.heading("GAPI", text="GAPI")
    tree.heading("✓", text="✓")
    
    # Base widths and stretch; we'll also auto-resize to fill 100% width
    tree.column("#", width=50, anchor="center", stretch=True)
    tree.column("Apt ID", width=80, anchor="center", stretch=True)
    tree.column("PreGAID", width=90, anchor="center", stretch=True)
    tree.column("Google", width=260, anchor="w", stretch=True)
    tree.column("Formatted", width=280, anchor="w", stretch=True)
    tree.column("Name", width=180, anchor="w", stretch=True)
    tree.column("Rating", width=60, anchor="center", stretch=True)
    tree.column("Reviews", width=70, anchor="center", stretch=True)
    tree.column("GAID", width=90, anchor="center", stretch=True)
    tree.column("GPID", width=100, anchor="center", stretch=True)
    tree.column("KC_ID", width=90, anchor="center", stretch=True)
    tree.column("Score", width=100, anchor="center", stretch=True)
    tree.column("Type", width=120, anchor="center", stretch=True)
    tree.column("GAPI", width=70, anchor="center", stretch=True)
    tree.column("✓", width=60, anchor="center", stretch=True)
    tree.column("KC_ID", width=90, anchor="center", stretch=True)
    tree.column("Score", width=100, anchor="center", stretch=True)
    tree.column("GAPI", width=70, anchor="center", stretch=True)
    tree.column("✓", width=60, anchor="center", stretch=True)

    # Enable sorting (asc/desc toggle) for all columns
    _sort_states = {}
    def _as_number(val: str):
        try:
            if val is None:
                return -float('inf')
            s = str(val)
            # Handle percentage like "92.3%"
            if s.endswith('%'):
                s = s[:-1]
            s = s.replace(',', '')
            return float(s)
        except Exception:
            return float('inf')

    def _sort_by(column_name: str):
        try:
            # Toggle direction
            descending = _sort_states.get(column_name, False)
            data = []
            for row_id in tree.get_children(''):
                v = tree.set(row_id, column_name)
                # Numeric-aware for some columns
                if column_name in ("#", "Apt ID", "Rating", "Reviews", "Score"):
                    key = _as_number(v)
                elif column_name in ("GAPI",):
                    # Sort GAPI: Cached first, then API types alphabetically
                    key = 0 if str(v).lower() == 'cached' else 1 if str(v) != '-' else 2
                else:
                    key = str(v).lower()
                data.append((key, row_id))
            data.sort(reverse=not descending)
            for index, (_k, iid) in enumerate(data):
                tree.move(iid, '', index)
            _sort_states[column_name] = not descending
        except Exception as e:
            log_to_file(f"[Address Match] sort error on '{column_name}': {e}")

    # Bind header clicks
    for c in cols:
        try:
            tree.heading(c, text=c, command=(lambda col=c: _sort_by(col)))
        except Exception:
            pass
    
    # Scrollbars: vertical and horizontal
    v_scrollbar = tk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    h_scrollbar = tk.Scrollbar(table_frame, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

    # Pack order: bottom horizontal bar, right vertical bar, then tree
    h_scrollbar.pack(side="bottom", fill="x")
    v_scrollbar.pack(side="right", fill="y")
    tree.pack(side="left", fill="both", expand=True)

    # Auto-fit columns to use 100% of available width with sensible weights
    col_weights = {
        "#": 40, "Apt ID": 50, "PreGAID": 80,
        "Google": 160, "Formatted": 180, "Name": 120, "Rating": 40,
        "Reviews": 50, "GAID": 90, "GPID": 100, "KC_ID": 60,
        "Score": 80, "Type": 100, "GAPI": 50, "✓": 35
    }
    min_widths = {
        "#": 50, "Apt ID": 70, "PreGAID": 80,
        "Google": 220, "Formatted": 240, "Name": 150, "Rating": 50,
        "Reviews": 60, "GAID": 90, "GPID": 100, "KC_ID": 70,
        "Score": 70, "Type": 100, "GAPI": 60, "✓": 50
    }

    def _resize_columns(event=None):
        try:
            total_weight = sum(col_weights.get(c, 100) for c in cols)
            avail = max(200, tree.winfo_width() - 18)  # account for scrollbar
            for c in cols:
                w = int(avail * (col_weights.get(c, 100) / total_weight))
                w = max(min_widths.get(c, 40), w)
                try:
                    tree.column(c, width=w)
                except Exception:
                    pass
        except Exception as e:
            log_to_file(f"[Address Match] resize columns error: {e}")

    # Bind window and tree size changes
    window.bind('<Configure>', lambda e: window.after(25, _resize_columns))
    tree.bind('<Configure>', lambda e: window.after(25, _resize_columns))
    # Initial sizing after layout
    window.after(50, _resize_columns)
    
    # Loading overlay to block interactions until table is fully populated (with ETA)
    is_loading = {"active": True}
    loader_overlay = tk.Frame(table_frame, bg="#111")
    loader_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
    loader_inner = tk.Frame(loader_overlay, bg="#111")
    loader_inner.place(relx=0.5, rely=0.5, anchor="center")
    loader_label = tk.Label(loader_inner, text="Loading listings...",
                            bg="#111", fg="#ECF0F1", font=("Segoe UI", 11, "bold"))
    loader_label.pack(pady=(0,6))
    # Use determinate mode to show progress and estimate
    loader_bar = ttk.Progressbar(loader_inner, mode='determinate', length=300)
    loader_bar.pack()
    try:
        loader_bar.configure(maximum=max(1, len(listings)), value=0)
    except Exception:
        pass

    def finish_loading():
        is_loading["active"] = False
        try:
            loader_bar.stop()
        except Exception:
            pass
        try:
            loader_overlay.place_forget()
            loader_overlay.destroy()
        except Exception:
            pass
    
    # Store results for viewing full responses
    results_cache = {}

    def open_full_response_for_row(row_values):
        """Open a window showing the full API response for the clicked row (pretty-print JSON if possible)."""
        try:
            idx = int(row_values[0])  # Row number stored in first column '#'
        except Exception:
            idx = None
        text_data = results_cache.get(idx)
        if not text_data:
            messagebox.showinfo("Response", "No response captured for this row yet.", parent=window)
            return
        
        # Check if this is an error response
        is_error = text_data.startswith("Error:")
        
        # Try to pretty print JSON if possible
        display_text = text_data
        try:
            parsed = json.loads(text_data)
            display_text = json.dumps(parsed, indent=2, ensure_ascii=False)
        except Exception:
            pass

        viewer = tk.Toplevel(window)
        title_prefix = "ERROR" if is_error else "API Response"
        viewer.title(f"{title_prefix} - Row {idx}")
        viewer.geometry("900x700")
        viewer.configure(bg="#1E1E1E")

        # Text area with scrollbar
        frame = tk.Frame(viewer, bg="#1E1E1E")
        frame.pack(fill="both", expand=True, padx=8, pady=8)
        sb = tk.Scrollbar(frame)
        sb.pack(side="right", fill="y")
        
        # Use red background for errors
        bg_color = "#8B0000" if is_error else "#2C3E50"
        txt = tk.Text(frame, bg=bg_color, fg="#ECF0F1", font=("Consolas", 10), wrap="none", yscrollcommand=sb.set)
        txt.pack(side="left", fill="both", expand=True)
        sb.config(command=txt.yview)
        # Horizontal scroll
        sbx = tk.Scrollbar(frame, orient="horizontal")
        sbx.pack(side="bottom", fill="x")
        txt.config(xscrollcommand=sbx.set)
        sbx.config(command=txt.xview)
        txt.insert("1.0", display_text)
        txt.config(state="disabled")

        # Buttons
        btn_frame = tk.Frame(viewer, bg="#1E1E1E")
        btn_frame.pack(fill="x", padx=8, pady=6)
        def copy_to_clip():
            try:
                viewer.clipboard_clear()
                viewer.clipboard_append(text_data)
            except Exception:
                pass
        tk.Button(btn_frame, text="Copy", command=copy_to_clip,
                  bg="#34495E", fg="#ECF0F1", relief="flat", padx=12, pady=5).pack(side="left")
        tk.Button(btn_frame, text="Close", command=viewer.destroy,
                  bg="#95A5A6", fg="#fff", relief="flat", padx=12, pady=5).pack(side="right")
    
    def run_for_address(row_id, google_address, preloaded_ga_id=None):
        """Run find_or_create_place.php for a specific google_address input; fill formatted_address after response.
        If preloaded_ga_id is provided, it will be used to look up the place_id for direct lookup.
        row_id: the tree item ID to update (not the row number)"""
        # Get the row number for logging and cache key
        try:
            values = tree.item(row_id, "values")
            idx = int(values[0])
        except Exception:
            idx = 0
            
        # Show loader
        tree.set(row_id, "✓", "⏳")
        try:
            # If we have a PreLoaded GA ID, try to get its place_id from the database
            place_id_to_use = None
            if preloaded_ga_id and preloaded_ga_id != "-":
                try:
                    conn = get_db_connection()
                    if not conn:
                        raise Exception("Failed to get DB connection")
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT place_id FROM google_addresses WHERE id = %s", (int(preloaded_ga_id),))
                    row = cursor.fetchone()
                    cursor.close()
                    # Don't close shared connection - it's reused
                    if row and row.get('place_id'):
                        place_id_to_use = row['place_id']
                        log_to_file(f"[Address Match] Found place_id '{place_id_to_use}' for GA ID {preloaded_ga_id}")
                except Exception as e:
                    log_to_file(f"[Address Match] Failed to lookup place_id for GA ID {preloaded_ga_id}: {e}")
            
            # Build URL - use place_id if available, otherwise use address
            if place_id_to_use:
                encoded_place_id = requests.utils.quote(place_id_to_use)
                url = php_url(f"step5/find_or_create_place.php?place_id={encoded_place_id}&html=yes&debug=1")
                log_to_file(f"[Address Match] Using place_id lookup: {place_id_to_use}")
            else:
                encoded_address = requests.utils.quote(google_address)
                url = php_url(f"step5/find_or_create_place.php?address={encoded_address}&html=yes&debug=1")
            
            # Use separate connect/read timeouts to avoid premature read timeouts on slower API paths
            # Connect: 8s, Read: 90s
            response = requests.get(url, timeout=(8, 90))
            result_text = response.text  # Store full response (error or JSON)
            results_cache[idx] = result_text
            
            # Try to parse JSON response to get all data
            try:
                result_json = json.loads(result_text)
                log_to_file(f"[Address Match] Raw JSON keys for {idx}: {list(result_json.keys())}")
                # If the API returned an explicit error, mark row red and stop
                try:
                    if result_json.get("ok") is False:
                        tree.set(row_id, "✓", "❌")
                        # Don't mark Skipped as 'No' on error; leave as-is so it doesn't count as an API call
                        tree.item(row_id, tags=("error",))
                        window.after(0, refresh_api_calls_tally)
                        return
                except Exception:
                    pass
                
                final_ids = result_json.get("final_ids", {})
                result = result_json.get("result", {})
                # Prefer apartment_listings_id provided by API to ensure correct mapping
                apt_id_from_api = (
                    result_json.get("apartment_listings_id")
                    or result.get("apartment_listings_id")
                )
                
                # Extract all fields from the response - check multiple possible locations for similarity_score
                # Check in these locations in order:
                # 1. root level "similarity_score"
                # 2. result.similarity_score
                # 3. final_ids.similarity_score (some APIs might put it here)
                # 4. If we have google_addresses_id and name, assume 100% match
                similarity_score = None
                
                # Try root level first
                if "similarity_score" in result_json and result_json["similarity_score"] is not None:
                    similarity_score = result_json["similarity_score"]
                    log_to_file(f"[Address Match] Found similarity_score at root level: {similarity_score}")
                
                # Try result object
                elif "similarity_score" in result and result["similarity_score"] is not None:
                    similarity_score = result["similarity_score"]
                    log_to_file(f"[Address Match] Found similarity_score in result: {similarity_score}")
                
                # Try final_ids object
                elif "similarity_score" in final_ids and final_ids["similarity_score"] is not None:
                    similarity_score = final_ids["similarity_score"]
                    log_to_file(f"[Address Match] Found similarity_score in final_ids: {similarity_score}")
                
                # If still not found, check if we have valid data (assume 100% match if API returned valid IDs)
                if similarity_score is None:
                    google_addresses_id_check = final_ids.get("google_addresses_id")
                    if google_addresses_id_check:
                        similarity_score = 100.0
                        log_to_file(f"[Address Match] No similarity_score found but have google_addresses_id, assuming 100%")
                    else:
                        similarity_score = 0
                        log_to_file(f"[Address Match] No similarity_score found and no valid IDs, defaulting to 0")
                
                # Convert to float if it's a string (handle formats like "92%" or "92.3")
                try:
                    if isinstance(similarity_score, str):
                        cleaned = ''.join(ch for ch in similarity_score if (ch.isdigit() or ch == '.'))
                        similarity_score = float(cleaned) if cleaned else 0.0
                    else:
                        similarity_score = float(similarity_score)
                except (ValueError, TypeError):
                    log_to_file(f"[Address Match] Could not convert similarity_score to float: {similarity_score}, using 0")
                    similarity_score = 0.0

                # Clamp to [0, 100]
                if similarity_score < 0:
                    similarity_score = 0.0
                elif similarity_score > 100:
                    similarity_score = 100.0
                
                # IMPORTANT: Reject low similarity scores to avoid wasting API calls on wrong addresses
                # Minimum threshold: 85% similarity (adjusted to be less strict)
                SIMILARITY_THRESHOLD = 85.0
                if similarity_score < SIMILARITY_THRESHOLD:
                    log_to_file(f"[Address Match] ⚠️ Row {idx}: Similarity {similarity_score:.1f}% below threshold {SIMILARITY_THRESHOLD}% - rejecting match to avoid wasting API call")
                    log_to_file(f"[Address Match] Input: {google_address}")
                    log_to_file(f"[Address Match] API returned: {result.get('formatted_address') or result_json.get('formatted_address', 'N/A')}")
                    # Mark as low similarity match (nomatch color)
                    tree.set(row_id, "✓", "⚠")
                    tree.set(row_id, "Score", f"{similarity_score:.1f}% ❌")
                    tree.set(row_id, "GAPI", "Low Sim")
                    tree.item(row_id, tags=("nomatch",))
                    window.after(0, refresh_api_calls_tally)
                    return  # Skip database update for low similarity matches
                
                # Check if API was skipped
                skipped_api_calls = result_json.get("skipped_api_calls", False)
                api_call_type = result_json.get("api_call_type", "-")
                
                # GAPI column: show API call type if API was called, or "Cached" if skipped
                if skipped_api_calls:
                    gapi_display = "Cached"
                else:
                    gapi_display = api_call_type if api_call_type and api_call_type != "-" else "Yes"
                    # Count as a NEW API call for this session
                    try:
                        new_api_calls_count.set(new_api_calls_count.get() + 1)
                    except Exception:
                        pass
                
                google_addresses_id = final_ids.get("google_addresses_id", "")
                google_places_id = final_ids.get("google_places_id", "")
                king_county_id = final_ids.get("king_county_id", "")
                
                # Extract place details from result - also check at root level
                name = result.get("name") or result_json.get("name", "-")
                rating_val = result.get("rating") or result_json.get("rating")
                reviews_val = result.get("user_ratings_total") or result_json.get("user_ratings_total")
                formatted_addr = result.get("formatted_address") or result_json.get("formatted_address") or "-"
                
                rating = str(rating_val) if rating_val else "-"
                user_ratings_total = str(reviews_val) if reviews_val else "-"
                
                # Extract place types from result
                place_type = "-"
                try:
                    types = result.get("types") or result_json.get("types") or []
                    if types and isinstance(types, list):
                        # Prioritize certain types for display
                        priority_types = ["apartment", "real_estate_agency", "property_management", "establishment", "lodging", "premise"]
                        for ptype in priority_types:
                            if ptype in types:
                                place_type = ptype.replace("_", " ").title()
                                break
                        # If no priority type, use first type
                        if place_type == "-" and types:
                            place_type = types[0].replace("_", " ").title()
                except Exception:
                    place_type = "-"
                
                # Update the tree with all fields (row_id already set at top of function)
                # If API provided authoritative apartment_listings_id, reflect it in the Apt ID column
                try:
                    if apt_id_from_api and str(tree.set(row_id, "Apt ID")) in ("", "-"):
                        tree.set(row_id, "Apt ID", str(apt_id_from_api))
                except Exception:
                    pass
                tree.set(row_id, "Name", name)
                tree.set(row_id, "Rating", rating)
                tree.set(row_id, "Reviews", user_ratings_total)
                tree.set(row_id, "Formatted", formatted_addr)
                # Always show DB value for GAID (not API); placeholder now, will refresh from DB below
                tree.set(row_id, "GAID", "-")
                tree.set(row_id, "GPID", google_places_id if google_places_id else "-")
                tree.set(row_id, "KC_ID", king_county_id if king_county_id else "-")
                tree.set(row_id, "Score", f"{similarity_score:.1f}%")
                tree.set(row_id, "Type", place_type)
                tree.set(row_id, "GAPI", gapi_display)
                # Update header tally
                window.after(0, refresh_api_calls_tally)

                # Update API usage stats from backend if available
                try:
                    stats = result_json.get("api_call_stats") or {}
                    t = int(stats.get("today", 0))
                    w = int(stats.get("last_week", 0))
                    m = int(stats.get("last_month", 0))
                    api_usage_var.set(f"API usage: today {t} • week {w} • month {m}")
                except Exception:
                    pass
                
                # Check if API indicates apartment_listings was updated
                api_updated = False
                try:
                    api_update_obj = result_json.get("apartment_listings_update")
                    if isinstance(api_update_obj, dict):
                        api_updated = bool(api_update_obj.get("updated", False))
                except Exception as _:
                    api_updated = False

                log_to_file(f"[Address Match] Extracted for {idx}: score={similarity_score}, name={name}, rating={rating}, reviews={user_ratings_total}, skipped={skipped_api_calls}, api_updated={api_updated}")
                
                # Track if database was updated
                db_updated = api_updated
                

                # Always update apartment_listings.google_addresses_id and google_places_id if google_addresses_id is present
                if google_addresses_id:
                    try:
                        conn = get_db_connection()
                        if not conn:
                            raise Exception("Failed to get DB connection")
                        cursor = conn.cursor(buffered=True)
                        
                        # Get apartment_listing_id from the UI table (Apt ID column) - most reliable source
                        apartment_listing_id = None
                        apt_id_str = None
                        try:
                            apt_id_str = tree.set(row_id, "Apt ID")
                            if apt_id_str and apt_id_str not in ("", "-"):
                                apartment_listing_id = apt_id_str
                                log_to_file(f"[Address Match] Using Apt ID from UI table: {apartment_listing_id}")
                        except Exception as e:
                            log_to_file(f"[Address Match] Failed to get Apt ID from UI: {e}")
                        
                        # Fallback: try to get from JSON listing if not in UI
                        if not apartment_listing_id:
                            try:
                                listing = listings[idx-1]
                                apartment_listing_id = listing.get("id")
                                log_to_file(f"[Address Match] Fallback to JSON listing ID: {apartment_listing_id}")
                            except Exception as e:
                                log_to_file(f"[Address Match] Failed to get ID from JSON: {e}")
                        
                        # Fallback: try to get from API response
                        if not apartment_listing_id and apt_id_from_api:
                            apartment_listing_id = apt_id_from_api
                            log_to_file(f"[Address Match] Fallback to API apartment_listings_id: {apartment_listing_id}")
                        
                        # Last resort: try listing_website or full_address from JSON
                        listing_website = None
                        full_address = None
                        google_address_for_lookup = None
                        if not apartment_listing_id:
                            try:
                                listing = listings[idx-1]
                                listing_website = listing.get("listing_website") or listing.get("url") or listing.get("link")
                                full_address = listing.get("full_address") or listing.get("address")
                                google_address_for_lookup = listing.get("google_address")
                                log_to_file(f"[Address Match] Will try lookup by: listing_website={listing_website}, full_address={full_address}, google_address={google_address_for_lookup}")
                            except Exception as e:
                                log_to_file(f"[Address Match] Failed to get lookup fields from JSON: {e}")
                        
                        rows_affected = 0
                        if apartment_listing_id:
                            cursor.execute("""
                                UPDATE apartment_listings 
                                SET google_addresses_id = %s, google_places_id = %s
                                WHERE id = %s
                            """, (google_addresses_id, google_places_id, apartment_listing_id))
                            rows_affected = cursor.rowcount
                            log_to_file(f"[Address Match] UPDATE by id={apartment_listing_id}: {rows_affected} rows affected")
                        elif listing_website:
                            cursor.execute("""
                                UPDATE apartment_listings 
                                SET google_addresses_id = %s, google_places_id = %s
                                WHERE listing_website = %s
                            """, (google_addresses_id, google_places_id, listing_website))
                            rows_affected = cursor.rowcount
                            log_to_file(f"[Address Match] UPDATE by listing_website: {rows_affected} rows affected")
                        elif full_address:
                            cursor.execute("""
                                UPDATE apartment_listings 
                                SET google_addresses_id = %s, google_places_id = %s
                                WHERE full_address = %s
                            """, (google_addresses_id, google_places_id, full_address))
                            rows_affected = cursor.rowcount
                            log_to_file(f"[Address Match] UPDATE by full_address='{full_address}': {rows_affected} rows affected")
                        elif google_address_for_lookup:
                            cursor.execute("""
                                UPDATE apartment_listings 
                                SET google_addresses_id = %s, google_places_id = %s
                                WHERE google_address = %s
                            """, (google_addresses_id, google_places_id, google_address_for_lookup))
                            rows_affected = cursor.rowcount
                            log_to_file(f"[Address Match] UPDATE by google_address='{google_address_for_lookup}': {rows_affected} rows affected")
                        else:
                            # No identifying fields available for UPDATE, will try INSERT
                            log_to_file(f"[Address Match] No identifying fields available (apt_id, listing_website, full_address, google_address all empty)")
                        
                        # If no rows updated and we have google_address, INSERT a new row
                        if rows_affected == 0:
                            # Try to get google_address from the UI if not in listing
                            if not google_address_for_lookup:
                                try:
                                    google_address_for_lookup = tree.set(row_id, "Google")
                                    log_to_file(f"[Address Match] Got google_address from UI: '{google_address_for_lookup}'")
                                except Exception as e:
                                    log_to_file(f"[Address Match] Failed to get google_address from UI: {e}")
                            
                            if google_address_for_lookup:
                                try:
                                    log_to_file(f"[Address Match] No existing row found, inserting new apartment_listings row for google_address='{google_address_for_lookup}'")
                                    cursor.execute("""
                                        INSERT INTO apartment_listings (google_address, google_addresses_id, google_places_id)
                                        VALUES (%s, %s, %s)
                                    """, (google_address_for_lookup, google_addresses_id, google_places_id))
                                    apartment_listing_id = cursor.lastrowid
                                    rows_affected = 1
                                    log_to_file(f"[Address Match] ✅ Inserted new apartment_listings row with id={apartment_listing_id}")
                                    # Update the UI with the new Apt ID
                                    tree.set(row_id, "Apt ID", str(apartment_listing_id))
                                    
                                    # Update statistics after inserting new row
                                    try:
                                        window.after(0, update_statistics)
                                    except Exception:
                                        pass
                                except Exception as insert_err:
                                    log_to_file(f"[Address Match] Failed to insert new row: {insert_err}")
                            else:
                                log_to_file(f"[Address Match] Cannot insert - no google_address available")
                        
                        # Note: autocommit=True in connection, so no manual commit needed
                        cursor.close()
                        # Don't close shared connection
                        if rows_affected > 0:
                            db_updated = True
                            action = "Inserted new" if apartment_listing_id and not apt_id_str else "Updated"
                            log_to_file(f"[Address Match] ✅ {action} {rows_affected} row(s) in DB for address {idx}: apartment_listing_id={apartment_listing_id}, google_addresses_id={google_addresses_id}, score={similarity_score}%")
                            # Don't show popup - just log it
                            # messagebox.showinfo("DB Update", f"✅ {action} row in DB for address {idx}\nApt ID: {apartment_listing_id}\nGA ID: {google_addresses_id}\nScore: {similarity_score}%", parent=window)
                        else:
                            log_to_file(f"[Address Match] ⚠️ No rows updated for address {idx} (score={similarity_score}%) - apt_id={apartment_listing_id}, listing_website={listing_website}, full_address={full_address}, google_address={google_address_for_lookup}")
                            # Don't show popup - just log it
                            # messagebox.showwarning("DB Update", f"No rows updated for address {idx}\nGA ID: {google_addresses_id}\nScore: {similarity_score}%\nCheck if the ID or address matches a row in apartment_listings.", parent=window)
                        # Regardless of update count, fetch the current google_addresses_id from DB and reflect it in the PreGAID column
                        try:
                            conn2 = get_db_connection()
                            if not conn2:
                                raise Exception("Failed to get DB connection")
                            cur2 = conn2.cursor()
                            # Choose the most reliable apartment_listings_id (API > resolved > JSON)
                            target_id = apt_id_from_api or apartment_listing_id or listing.get("id")
                            if target_id:
                                cur2.execute("SELECT google_addresses_id FROM apartment_listings WHERE id = %s LIMIT 1", (target_id,))
                                row_ga = cur2.fetchone()
                                if row_ga and row_ga[0] not in (None, ""):
                                    tree.set(row_id, "PreGAID", f"{row_ga[0]} 🗑")
                                    # Also ensure Apt ID column is set to this target_id if missing
                                    try:
                                        if str(tree.set(row_id, "Apt ID")) in ("", "-"):
                                            tree.set(row_id, "Apt ID", str(target_id))
                                    except Exception:
                                        pass
                            cur2.close()
                            # Don't close shared connection
                        except Exception as e:
                            log_to_file(f"[Address Match] Failed to refresh PreGAID from DB: {e}")
                    except Exception as db_err:
                        log_to_file(f"[Address Match] Failed to update DB for address {idx}: {db_err}")

                # NOTE: Name, Rating, Reviews are already set from API response above (lines 6664-6667)
                # We do NOT fetch from google_addresses table here because Play button should use fresh API data


                # Refresh both PreGAID and GAID directly from DB (authoritative source)
                try:
                    apt_lookup_id = None
                                    # Background processing (replicates show_insert_db_window logic)
                    try:
                        existing_apt = tree.set(row_id, "Apt ID")
                        if existing_apt and existing_apt not in ("", "-"):
                            apt_lookup_id = existing_apt
                    except Exception:
                        pass
                    if (not apt_lookup_id) and apt_id_from_api:
                        apt_lookup_id = str(apt_id_from_api)
                    if apt_lookup_id:
                        conn = get_db_connection()
                        if not conn:
                            raise Exception("Failed to get DB connection")
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute("SELECT google_addresses_id FROM apartment_listings WHERE id = %s", (apt_lookup_id,))
                        arow = cursor.fetchone()
                        cursor.close()
                        # Don't close shared connection
                        db_ga_id = arow.get("google_addresses_id") if arow else None
                        tree.set(row_id, "PreGAID", (f"{db_ga_id} 🗑" if db_ga_id not in (None, "") else "-"))
                        tree.set(row_id, "GAID", (str(db_ga_id) if db_ga_id not in (None, "") else "-"))
                        
                        # Update statistics after changes
                        try:
                            window.after(0, update_statistics)
                        except Exception:
                            pass
                except Exception as e:
                    log_to_file(f"[Address Match] Failed to refresh GAID from DB: {e}")

                # Show explicit result: ✓ if updated, X if not
                tree.set(row_id, "✓", "✓" if db_updated else "X")

                # Color the row based on outcome
                try:
                    if google_addresses_id:
                        zebra_tag = "odd" if (idx % 2 == 1) else "even"
                        tree.item(row_id, tags=(zebra_tag,))
                    else:
                        tree.item(row_id, tags=("nomatch",))
                except Exception:
                    pass
                
            except json.JSONDecodeError as json_err:
                # Bad/Non-JSON response; mark row as error but do not flag Skipped as 'No'
                log_to_file(f"[Address Match] JSON decode error for row {idx}: {json_err}")
                # Prepend error message to cached response for better visibility
                if idx in results_cache:
                    results_cache[idx] = f"Error: Invalid JSON response\n{json_err}\n\n=== Raw Response ===\n{results_cache[idx]}"
                try:
                    tree.item(row_id, tags=("error",))
                except Exception:
                    pass
                window.after(0, refresh_api_calls_tally)
            
            # Ensure the action column reflects completion; default to X if not explicitly set
            try:
                current_val = tree.set(row_id, "✓")
                if current_val not in ("✓", "X", "❌"):
                    tree.set(row_id, "✓", "X")
            except Exception:
                pass
            log_to_file(f"[Address Match] Processed address {idx}: {google_address}")
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            results_cache[idx] = error_msg
            tree.set(row_id, "✓", "❌")
            log_to_file(f"[Address Match] Error for address {idx}: {e}")
            # Do not mark Skipped as 'No' on errors; leave as-is so it doesn't count as an API call
            # Mark as error visually
            try:
                tree.item(row_id, tags=("error",))
            except Exception:
                pass
            window.after(0, refresh_api_calls_tally)
    
    # Try to get DB connection for prefetch (will reuse shared connection)
    db_conn = get_db_connection()
    db_cursor = None
    if db_conn:
        try:
            db_cursor = db_conn.cursor(buffered=True)
        except Exception as _e:
            log_to_file(f"[Address Match] AptID prefetch cursor failed: {_e}")
            db_cursor = None
    else:
        log_to_file(f"[Address Match] AptID prefetch DB connect failed")

    # Populate table with progress/ETA
    total_listings = len(listings)
    t0 = time.time()
    def _fmt_secs(sec: float) -> str:
        sec = max(0, int(sec))
        m, s = divmod(sec, 60)
        return f"{m:02d}:{s:02d}"

    # Reset master row list before populating
    try:
        all_row_ids.clear()
    except Exception:
        pass

    for i, listing in enumerate(listings, 1):
        google_address = listing.get("google_address", "N/A")
        # JSON-provided IDs (raw)
        json_google_addresses_id = listing.get("google_addresses_id", "")
        json_google_places_id = listing.get("google_places_id", "")
        king_county_id = listing.get("king_county_id", "")
        # Try multiple keys commonly used for apartment listing id
        apartment_listing_id = (
            listing.get("id")
            or listing.get("apartment_listings_id")
            or listing.get("apartment_id")
            or listing.get("apt_id")
            or ""
        )  # Try to use provided ID first
        
        # Removed verbose log: JSON keys available

        # If missing, try to find by listing_website or full_address
        if (not apartment_listing_id) and db_cursor is not None:
            try:
                listing_website = listing.get("listing_website") or listing.get("url") or listing.get("link")
                full_address = listing.get("full_address") or listing.get("address")
                if listing_website:
                    db_cursor.execute("SELECT id FROM apartment_listings WHERE listing_website = %s LIMIT 1", (listing_website,))
                    row = db_cursor.fetchone()
                    if row and row[0]:
                        apartment_listing_id = row[0]
                if (not apartment_listing_id) and full_address:
                    db_cursor.execute("SELECT id FROM apartment_listings WHERE full_address = %s LIMIT 1", (full_address,))
                    row = db_cursor.fetchone()
                    if row and row[0]:
                        apartment_listing_id = row[0]
            except Exception as e:
                log_to_file(f"[Address Match] AptID prefetch query failed for row {i}: {e}")
        
    # If we have the apartment_listing_id, prefetch any existing google_addresses_id / google_places_id
        preloaded_ga_id = ""
        preloaded_gp_id = ""
        prefilled_name = "-"
        prefilled_rating = "-"
        prefilled_reviews = "-"
        prefilled_formatted = "-"
        prefilled_match_score = "-"
        prefilled_type = "-"
        
        if apartment_listing_id and db_cursor is not None:
            try:
                db_cursor.execute(
                    "SELECT google_addresses_id, google_places_id FROM apartment_listings WHERE id = %s LIMIT 1",
                    (apartment_listing_id,)
                )
                row = db_cursor.fetchone()
                # Removed verbose log: DB row details
                if row:
                    db_ga_id, db_gp_id = row
                    if db_ga_id is not None and str(db_ga_id).strip() != "":
                        preloaded_ga_id = db_ga_id
                        # Removed verbose log: Found PreLoaded GA ID
                        # Fetch details from google_addresses table including json_dump
                        try:
                            db_cursor.execute(
                                "SELECT building_name, initial_review_rating, initial_review_count, json_dump FROM google_addresses WHERE id = %s LIMIT 1",
                                (db_ga_id,)
                            )
                            ga_row = db_cursor.fetchone()
                            if ga_row:
                                ga_name, ga_rating, ga_reviews, json_dump = ga_row
                                ga_formatted = None  # We'll get this from json_dump
                                log_to_file(f"[Address Match] Row {i}: GA data - building_name={ga_name}, rating={ga_rating}, reviews={ga_reviews}")
                                
                                # Try to parse json_dump for more complete data
                                if json_dump:
                                    try:
                                        dump_data = json.loads(json_dump)
                                        # The actual data is under the "result" key
                                        result = dump_data.get("result", {})
                                        if result:
                                            # Get formatted_address from json_dump (not stored as separate column)
                                            if result.get("formatted_address"):
                                                ga_formatted = result["formatted_address"]
                                            # Override with json_dump data if available (for name, rating, reviews)
                                            if result.get("name"):
                                                ga_name = result["name"]
                                            if result.get("rating") is not None:
                                                ga_rating = result["rating"]
                                            if result.get("user_ratings_total") is not None:
                                                ga_reviews = result["user_ratings_total"]
                                            # Extract place types
                                            types = result.get("types") or []
                                            if types and isinstance(types, list):
                                                priority_types = ["apartment", "real_estate_agency", "property_management", "establishment", "lodging", "premise"]
                                                for ptype in priority_types:
                                                    if ptype in types:
                                                        prefilled_type = ptype.replace("_", " ").title()
                                                        break
                                                if prefilled_type == "-" and types:
                                                    prefilled_type = types[0].replace("_", " ").title()
                                            log_to_file(f"[Address Match] Row {i}: Enhanced from json_dump - name={ga_name}, formatted={ga_formatted}, rating={ga_rating}, reviews={ga_reviews}")
                                    except Exception as json_err:
                                        log_to_file(f"[Address Match] Row {i}: Failed to parse json_dump: {json_err}")
                                # Use google_addresses data to fill empty fields
                                json_name = listing.get("name") or listing.get("google_name") or ""
                                json_formatted = listing.get("formatted_address") or listing.get("formatted") or ""
                                json_rating = listing.get("rating")
                                json_reviews = listing.get("user_ratings_total") or listing.get("reviews")
                                
                                # Use JSON if present, otherwise use GA table values
                                prefilled_name = json_name if json_name else (ga_name or "-")
                                prefilled_formatted = json_formatted if json_formatted else (ga_formatted or "-")
                                prefilled_rating = str(json_rating) if json_rating not in (None, "", 0) else (str(ga_rating) if ga_rating not in (None, "", 0) else "-")
                                prefilled_reviews = str(json_reviews) if json_reviews not in (None, "", 0) else (str(ga_reviews) if ga_reviews not in (None, "", 0) else "-")
                                
                                # Removed verbose log: Prefilled details
                                
                                # Calculate match score between google_address and formatted_address
                                google_address = listing.get("google_address", "")
                                if google_address and ga_formatted:
                                    import difflib
                                    norm_input = re.sub(r'\W', '', google_address.lower())
                                    norm_candidate = re.sub(r'\W', '', ga_formatted.lower())
                                    match_ratio = difflib.SequenceMatcher(None, norm_input, norm_candidate).ratio()
                                    prefilled_match_score = f"{int(match_ratio * 100)}%"
                                
                        except Exception as ga_err:
                            log_to_file(f"[Address Match] Failed to prefetch GA details for id {db_ga_id}: {ga_err}")
                    if db_gp_id not in (None, ""):
                        preloaded_gp_id = db_gp_id
            except Exception as e:
                log_to_file(f"[Address Match] GA/GPlace prefetch failed for id {apartment_listing_id}: {e}")
        
        # Name, Rating, Reviews, Formatted will be populated when Play button is clicked (or prefilled if GA ID exists)
        name = prefilled_name
        rating = prefilled_rating
        reviews = prefilled_reviews
        formatted_addr = prefilled_formatted
        match_score = prefilled_match_score
        place_type = prefilled_type
        
        zebra_tag = "odd" if (i % 2 == 1) else "even"
        # Show clear icon in PreGAID if it exists
        preloaded_display = f"{preloaded_ga_id} 🗑" if preloaded_ga_id else "-"
        # Combine match_score into Score column (show both if match exists)
        score_display = match_score if match_score != "-" else "-"
        rid = tree.insert("", "end", values=(
            i,
            apartment_listing_id if apartment_listing_id else "-",  # Apt ID
            preloaded_display,  # PreGAID with clear icon if exists
            google_address,
            formatted_addr,
            name,
            rating,
            reviews,
            str(preloaded_ga_id) if preloaded_ga_id else "-",  # GAID
            json_google_places_id if json_google_places_id else "-",  # GPID
            king_county_id if king_county_id else "-",
            score_display,  # Score (includes match percentage)
            place_type,  # Type (from json_dump types field)
            "-",  # GAPI placeholder (will show API call type or status)
            "▶"
        ), tags=(zebra_tag,))
        try:
            all_row_ids.append(rid)
        except Exception:
            pass

        # Update progress bar and ETA every few rows (or every row for responsiveness)
        try:
            elapsed = time.time() - t0
            avg = (elapsed / i) if i > 0 else 0
            remaining = max(0.0, (total_listings - i) * avg)
            pct = int((i / total_listings) * 100) if total_listings > 0 else 100
            loader_bar.configure(value=i)
            loader_label.config(text=f"Loading listings… {i}/{total_listings} ({pct}%) • elapsed {_fmt_secs(elapsed)} • ETA {_fmt_secs(remaining)}")
            window.update_idletasks()
        except Exception:
            pass

    # Close prefetch DB cursor (but keep shared connection alive)
    try:
        if db_cursor is not None:
            db_cursor.close()
        # Don't close shared connection - it's reused throughout window lifetime
    except Exception:
        pass

    # Remove loader overlay now that the table is populated
    try:
        finish_loading()
    except Exception as e:
        log_to_file(f"[Address Match] finish_loading error: {e}")
    
    # Update statistics and apply filters
    try:
        update_statistics()
        recompute_row_visibility()
    except Exception as e:
        log_to_file(f"[Address Match] Initial statistics/filter error: {e}")
    
    # Check completion after a short delay (in case all PreGAIDs are already filled)
    def check_initial_completion():
        try:
            update_statistics()  # Re-check to trigger auto-close if 100% complete
        except Exception as e:
            log_to_file(f"[Address Match] Initial completion check error: {e}")
    window.after(1000, check_initial_completion)

    # Real-time search filter uses the unified recompute function
    search_var.trace_add('write', lambda *_: recompute_row_visibility())
    # Focus search bar after window loads
    window.after(100, lambda: search_entry.focus_set())
    
    # Auto-start: enable Auto Update shortly after window opens
    def _auto_start_update():
        try:
            # Only start if not already running and not loading
            if not auto_update_running.get("active"):
                auto_update_var.set(True)
                toggle_auto_update()
                log_to_file("[Address Match] Auto-update auto-started")
        except Exception as _e:
            log_to_file(f"[Address Match] Auto-start error: {_e}")
    window.after(400, _auto_start_update)

    
    # Handle clicks on checkbox and action columns
    def on_click(event):
        if is_loading["active"]:
            return
        region = tree.identify_region(event.x, event.y)
        if region == "cell":
            col = tree.identify_column(event.x)
            row_id = tree.identify_row(event.y)
            
            # PreGAID column (#3) - click on trash icon to clear
            if col == "#3" and row_id:
                values = tree.item(row_id, "values")
                preloaded_val = values[2]  # PreGAID column (index 2)
                apt_id = values[1]  # Apt ID column (index 1)
                # Check if there's a 🗑 icon (meaning there's a PreGAID to clear)
                if "🗑" in str(preloaded_val) and apt_id and apt_id != "-":
                    def clear_preloaded_ga_id():
                        try:
                            conn = get_db_connection()
                            if not conn:
                                raise Exception("Failed to get DB connection")
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE apartment_listings SET google_addresses_id = NULL WHERE id = %s",
                                (apt_id,)
                            )
                            # Note: autocommit=True in connection, so no manual commit needed
                            cursor.close()
                            # Don't close shared connection
                            
                            # Update UI: clear PreGAID and reset prefilled fields
                            tree.set(row_id, "PreGAID", "-")
                            tree.set(row_id, "GAID", "-")
                            tree.set(row_id, "Name", "-")
                            tree.set(row_id, "Rating", "-")
                            tree.set(row_id, "Reviews", "-")
                            tree.set(row_id, "Formatted", "-")
                            tree.set(row_id, "Score", "-")
                            tree.set(row_id, "Type", "-")
                            log_to_file(f"[Address Match] Cleared PreGAID for apartment_listings id {apt_id}")
                            messagebox.showinfo("Cleared", f"PreGAID cleared for row {apt_id}", parent=window)
                        except Exception as e:
                            log_to_file(f"[Address Match] Failed to clear PreGAID for id {apt_id}: {e}")
                            messagebox.showerror("Error", f"Failed to clear: {e}", parent=window)
                    threading.Thread(target=clear_preloaded_ga_id, daemon=True).start()
            
            # Action column (Play button) - run for this address (last column now #15)
            elif col == "#15" and row_id:  # Last column: action/status
                try:
                    values = tree.item(row_id, "values")
                    idx = int(values[0])  # Row number for logging (first column)
                    google_address = values[3]  # Google address (4th column)
                    preloaded_ga_raw = values[2]  # PreGAID (3rd column, may have trash icon)
                    # Strip the trash icon if present
                    preloaded_ga_id = str(preloaded_ga_raw).replace(" 🗑", "").strip() if preloaded_ga_raw and preloaded_ga_raw != "-" else None
                    
                    log_to_file(f"[Address Match] Play clicked for row_id={row_id}, row#={idx}, address={google_address}, preloaded_ga_id={preloaded_ga_id}")
                    
                    # Run in background thread - pass row_id instead of idx
                    threading.Thread(target=run_for_address, args=(row_id, google_address, preloaded_ga_id), daemon=True).start()
                except Exception as play_err:
                    log_to_file(f"[Address Match] Play button error: {play_err}")
                    import traceback
                    log_to_file(f"[Address Match] Play button traceback: {traceback.format_exc()}")
                    messagebox.showerror("Error", f"Failed to start address match: {play_err}", parent=window)
    
    tree.bind("<Button-1>", on_click)
    
    # Double-click to view full cell content in a pop-out (prevents hidden/truncated data)
    def on_double_click(event):
        if is_loading["active"]:
            return
        try:
            region = tree.identify_region(event.x, event.y)
            if region != "cell":
                return
            col_id = tree.identify_column(event.x)  # like '#5'
            row_id = tree.identify_row(event.y)
            if not row_id or not col_id:
                return
            # Map column index to name
            try:
                idx = int(col_id.replace('#','')) - 1
                col_name = cols[idx]
            except Exception:
                col_name = col_id
            val = tree.set(row_id, col_name)

            viewer = tk.Toplevel(window)
            viewer.title(f"Cell: {col_name}")
            viewer.geometry("800x250")
            viewer.configure(bg="#1E1E1E")
            frame = tk.Frame(viewer, bg="#1E1E1E")
            frame.pack(fill="both", expand=True, padx=8, pady=8)
            ysb = tk.Scrollbar(frame)
            ysb.pack(side="right", fill="y")
            xsb = tk.Scrollbar(frame, orient="horizontal")
            xsb.pack(side="bottom", fill="x")
            txt = tk.Text(frame, bg="#2C3E50", fg="#ECF0F1", font=("Consolas", 10), wrap="none",
                          yscrollcommand=ysb.set, xscrollcommand=xsb.set)
            txt.pack(side="left", fill="both", expand=True)
            ysb.config(command=txt.yview)
            xsb.config(command=txt.xview)
            txt.insert("1.0", str(val))
            txt.config(state="disabled")

            btn_frame = tk.Frame(viewer, bg="#1E1E1E")
            btn_frame.pack(fill="x", padx=8, pady=6)
            def _copy():
                try:
                    viewer.clipboard_clear()
                    viewer.clipboard_append(str(val))
                except Exception:
                    pass
            tk.Button(btn_frame, text="Copy", command=_copy,
                      bg="#34495E", fg="#ECF0F1", relief="flat", padx=12, pady=5).pack(side="left")
            tk.Button(btn_frame, text="Close", command=viewer.destroy,
                      bg="#95A5A6", fg="#fff", relief="flat", padx=12, pady=5).pack(side="right")
        except Exception as e:
            log_to_file(f"[Address Match] on_double_click error: {e}")

    tree.bind("<Double-1>", on_double_click)
    
    # On right-click, open full response viewer (no hover tooltips)
    def on_row_right_click(event):
        if is_loading["active"]:
            return
        try:
            row_id = tree.identify_row(event.y)
            if not row_id:
                return
            col = tree.identify_column(event.x)
            values = tree.item(row_id, "values")
            if not values:
                return
            
            # If right-clicked on Apt ID column (#2), show apartment_listings details
            if col == "#2":
                apt_id = values[1]  # Apt ID is second column (index 1)
                if apt_id and apt_id != "-":
                    show_apartment_listing_details(apt_id)
                else:
                    messagebox.showinfo("No Apt ID", "This row has no Apartment Listing ID.", parent=window)
            else:
                # Otherwise show API response
                open_full_response_for_row(values)
        except Exception as e:
            log_to_file(f"[Address Match] on_row_right_click error: {e}")
    
    def show_apartment_listing_details(apt_id):
        """Show all apartment_listings data for the given ID in a formatted window."""
        try:
            conn = get_db_connection()
            if not conn:
                messagebox.showerror("Database Error", "Failed to connect to database", parent=window)
                return
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM apartment_listings WHERE id = %s", (apt_id,))
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                messagebox.showinfo("Not Found", f"No apartment_listings record found for ID {apt_id}", parent=window)
                return
            
            # Create viewer window
            viewer = tk.Toplevel(window)
            viewer.title(f"Apartment Listing Details - ID {apt_id}")
            viewer.geometry("800x600")
            viewer.configure(bg="#1E1E1E")
            
            # Header
            header = tk.Label(viewer, text=f"Apartment Listing ID: {apt_id}", 
                            bg="#2C3E50", fg="#ECF0F1", font=("Segoe UI", 14, "bold"), pady=10)
            header.pack(fill="x")
            
            # Scrollable frame for data
            canvas = tk.Canvas(viewer, bg="#1E1E1E", highlightthickness=0)
            scrollbar = tk.Scrollbar(viewer, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#1E1E1E")
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Display each field
            fields_to_display = [
                ("ID", "id"),
                ("Google Address", "google_address"),
                ("Google Addresses ID", "google_addresses_id"),
                ("Google Places ID", "google_places_id"),
                ("Listing Website", "listing_website"),
                ("Full Address", "full_address"),
                ("Apartment Name", "apartment_name"),
                ("City", "city"),
                ("State", "state"),
                ("Zip Code", "zip_code"),
                ("Bedrooms", "bedrooms"),
                ("Bathrooms", "bathrooms"),
                ("Rent", "rent"),
                ("Deposit", "deposit"),
                ("Square Feet", "square_feet"),
                ("Available Date", "available_date"),
                ("Pet Policy", "pet_policy"),
                ("Parking", "parking"),
                ("Utilities Included", "utilities_included"),
                ("Amenities", "amenities"),
                ("Description", "description"),
                ("Contact Name", "contact_name"),
                ("Contact Phone", "contact_phone"),
                ("Contact Email", "contact_email"),
                ("Image URLs", "image_urls"),
                ("Date Added", "date_added"),
                ("Last Updated", "last_updated"),
                ("Status", "status"),
                ("Source", "source"),
                ("External ID", "external_id"),
            ]
            
            for label, field in fields_to_display:
                if field in row:
                    value = row[field]
                    if value is None:
                        value = "-"
                    
                    # Create frame for each field
                    field_frame = tk.Frame(scrollable_frame, bg="#2C3E50", padx=10, pady=5)
                    field_frame.pack(fill="x", padx=10, pady=2)
                    
                    # Label
                    lbl = tk.Label(field_frame, text=f"{label}:", 
                                 bg="#2C3E50", fg="#3498DB", font=("Segoe UI", 10, "bold"), anchor="w", width=20)
                    lbl.pack(side="left", padx=(0, 10))
                    
                    # Value (with word wrap for long text)
                    val_text = str(value)
                    if len(val_text) > 100:
                        # Use Text widget for long values
                        val_frame = tk.Frame(field_frame, bg="#34495E")
                        val_frame.pack(side="left", fill="both", expand=True)
                        val_widget = tk.Text(val_frame, bg="#34495E", fg="#ECF0F1", 
                                           font=("Consolas", 9), wrap="word", height=3, relief="flat")
                        val_widget.insert("1.0", val_text)
                        val_widget.config(state="disabled")
                        val_widget.pack(fill="both", expand=True, padx=2, pady=2)
                    else:
                        # Use Label for short values
                        val = tk.Label(field_frame, text=val_text, 
                                     bg="#34495E", fg="#ECF0F1", font=("Consolas", 9), 
                                     anchor="w", wraplength=500, justify="left", padx=5, pady=3)
                        val.pack(side="left", fill="x", expand=True)
            
            canvas.pack(side="left", fill="both", expand=True, padx=10, pady=10)
            scrollbar.pack(side="right", fill="y")
            
            # Buttons
            btn_frame = tk.Frame(viewer, bg="#1E1E1E")
            btn_frame.pack(fill="x", padx=10, pady=10)
            
            def copy_all():
                try:
                    text = f"Apartment Listing ID: {apt_id}\n" + "="*50 + "\n\n"
                    for label, field in fields_to_display:
                        if field in row:
                            value = row[field] if row[field] is not None else "-"
                            text += f"{label}: {value}\n"
                    viewer.clipboard_clear()
                    viewer.clipboard_append(text)
                    messagebox.showinfo("Copied", "All data copied to clipboard", parent=viewer)
                except Exception as e:
                    log_to_file(f"[Address Match] Copy error: {e}")
            
            tk.Button(btn_frame, text="Copy All", command=copy_all,
                     bg="#34495E", fg="#ECF0F1", relief="flat", padx=12, pady=5).pack(side="left")
            tk.Button(btn_frame, text="Close", command=viewer.destroy,
                     bg="#95A5A6", fg="#fff", relief="flat", padx=12, pady=5).pack(side="right")
            
        except Exception as e:
            log_to_file(f"[Address Match] show_apartment_listing_details error: {e}")
            messagebox.showerror("Error", f"Failed to load apartment details: {e}", parent=window)

    tree.bind("<Button-3>", on_row_right_click)
    
    # Auto-update state
    auto_update_running = {"active": False, "current_index": 0}
    
    def update_job_status_to_done():
        """Update the queue_websites job status to 'done' and update timestamps when all address matches are completed."""
        try:
            import requests
            from datetime import datetime
            import mysql.connector
            
            # Note: job_id here is actually the network ID (source_id), not queue_websites.id
            # Update all queue_websites rows with this source_id
            
            # Update status and timestamps directly in database
            try:
                conn = mysql.connector.connect(
                    host=CFG["MYSQL_HOST"],
                    user=CFG["MYSQL_USER"],
                    password=CFG["MYSQL_PASSWORD"],
                    database=CFG.get("MYSQL_DB", "offta"),
                    port=int(CFG.get("MYSQL_PORT", 3306)),
                    connection_timeout=10
                )
                cursor = conn.cursor()
                
                # Update using source_id - use correct column names: processed_at and updated_at
                cursor.execute("""
                    UPDATE queue_websites 
                    SET processed_at = NOW(), updated_at = NOW(), status = 'done'
                    WHERE source_id = %s
                """, (job_id,))
                
                rows_updated = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()
                
                if rows_updated > 0:
                    log_to_file(f"[Address Match] Updated {rows_updated} queue_websites row(s) to 'done' with source_id={job_id}")
                else:
                    log_to_file(f"[Address Match] No queue_websites rows found with source_id={job_id}")
            except Exception as db_err:
                log_to_file(f"[Address Match] Failed to update status/timestamps: {db_err}")
                
        except Exception as e:
            log_to_file(f"[Address Match] Error updating job status to done: {e}")
            print(f"[Address Match] Error updating job status: {e}")
    
    def process_next_row():
        """Process the next eligible row in auto-update mode (skip rows with PreGAID and rows without Apt ID)."""
        if not auto_update_running["active"]:
            return

        all_rows = tree.get_children()
        current_idx = auto_update_running["current_index"]

        # Advance to the next row that is not terminal and has no preloaded GA ID
        while current_idx < len(all_rows):
            row_id = all_rows[current_idx]
            try:
                status_val = tree.set(row_id, "✓")  # safer than index
            except Exception:
                status_val = ""

            try:
                preloaded_ga_val = tree.set(row_id, "PreGAID")
            except Exception:
                preloaded_ga_val = ""
            
            try:
                apt_id_val = tree.set(row_id, "Apt ID")
            except Exception:
                apt_id_val = ""

            # Skip if row already has a terminal status
            if status_val in ("✓", "X", "❌"):
                current_idx += 1
                continue
            
            # Skip if row has no Apt ID
            if apt_id_val in ("", "-"):
                current_idx += 1
                continue

            # Skip if PreGAID exists
            if preloaded_ga_val not in ("", "-"):
                current_idx += 1
                continue

            # Found an eligible row to process
            break

        # Update the shared index pointer
        auto_update_running["current_index"] = current_idx

        # If no eligible rows remain, finish
        if current_idx >= len(all_rows):
            auto_update_running["active"] = False
            auto_update_running["current_index"] = 0
            try:
                auto_update_var.set(False)
            except Exception:
                pass
            log_to_file("[Address Match] Auto-update completed (no eligible rows left)")
            
            # Check if there are any rows without PreGAID
            has_empty_pregaid = False
            for check_row_id in tree.get_children():
                try:
                    check_pregaid = tree.set(check_row_id, "PreGAID")
                    if check_pregaid in ("", "-"):
                        has_empty_pregaid = True
                        break
                except Exception:
                    pass
            
            # Only mark as done if no empty PreGAID rows remain
            if not has_empty_pregaid:
                log_to_file("[Address Match] No more empty PreGAID rows - marking job as done")
                update_job_status_to_done()
                # Notify Activity Window if a callback was registered
                try:
                    ADDRESS_MATCH_CALLBACKS = get_address_match_callbacks()
                    cb = ADDRESS_MATCH_CALLBACKS.get(str(job_id)) or ADDRESS_MATCH_CALLBACKS.get(job_id)
                    if cb:
                        cb(int(new_api_calls_count.get()))
                        # Clear callback so it won't be called twice
                        ADDRESS_MATCH_CALLBACKS.pop(str(job_id), None)
                        ADDRESS_MATCH_CALLBACKS.pop(job_id, None)
                except Exception as _cb_e:
                    log_to_file(f"[Address Match] Callback error: {_cb_e}")
                    # Close the Address Match window after marking done (only if opened by automation)
                    if not manual_open:
                        log_to_file("[Address Match] Auto-closing window (opened by automation)")
                        window.after(2000, window.destroy)  # Close after 2 seconds
                    else:
                        log_to_file("[Address Match] Window opened manually - keeping open")
                    # OLD CODE - Always closed window
                try:
                        pass
                except Exception:
                    pass
            else:
                log_to_file("[Address Match] Still have empty PreGAID rows - not marking as done")
            return

        # Process the selected row
        row_id = all_rows[current_idx]
        try:
            idx_str = tree.set(row_id, "#")
            idx = int(idx_str) if idx_str else (current_idx + 1)
        except Exception:
            idx = current_idx + 1

        try:
            google_address = tree.set(row_id, "Google")
            preloaded_ga_id = tree.set(row_id, "PreGAID")
        except Exception:
            # Fallback using values by index if needed
            vals = tree.item(row_id, "values")
            google_address = vals[3] if len(vals) > 3 else ""  # Google is 4th column (index 3)
            preloaded_ga_id = vals[2] if len(vals) > 2 else None  # PreGAID is 3rd column (index 2)

        log_to_file(f"[Address Match] Auto-update processing row {idx}/{len(all_rows)} (no PreGAID)")

        # Create a wrapper that calls process_next_row after completion
        def run_and_continue():
            run_for_address(row_id, google_address, preloaded_ga_id)
            # Wait a bit then process next row
            auto_update_running["current_index"] = current_idx + 1
            window.after(2000, process_next_row)  # 2 second delay between rows

        threading.Thread(target=run_and_continue, daemon=True).start()
    
    def toggle_auto_update():
        """Toggle auto-update mode."""
        if is_loading["active"]:
            try:
                auto_update_var.set(False)
            except Exception:
                pass
            log_to_file("[Address Match] Auto-update ignored while loading")
            return
        if auto_update_var.get():
            # Start auto-update
            auto_update_running["active"] = True
            auto_update_running["current_index"] = 0
            log_to_file("[Address Match] Auto-update started")
            process_next_row()
        else:
            # Stop auto-update
            auto_update_running["active"] = False
            log_to_file("[Address Match] Auto-update stopped")
    
    # Bottom buttons
    btn_frame = tk.Frame(window, bg="#1E1E1E")
    btn_frame.pack(pady=5)
    
    def refresh_table():
        """Re-read the JSON and repopulate the table with fresh DB preloads and loader/ETA."""
        try:
            # Stop auto-update if running
            try:
                auto_update_running["active"] = False
                auto_update_var.set(False)
            except Exception:
                pass

            # Reset header API calls count
            try:
                api_calls_count.set(0)
                update_header_text()
            except Exception:
                pass

            # Re-read JSON from disk (if changed)
            new_listings = listings
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    new_listings = json.load(f)
            except Exception as e:
                log_to_file(f"[Address Match] Refresh: failed to re-read JSON, using previous in-memory data: {e}")

            # Show a fresh loader overlay
            local_overlay = tk.Frame(table_frame, bg="#111")
            local_overlay.place(relx=0, rely=0, relwidth=1, relheight=1)
            local_inner = tk.Frame(local_overlay, bg="#111")
            local_inner.place(relx=0.5, rely=0.5, anchor="center")
            local_label = tk.Label(local_inner, text="Refreshing listings...", bg="#111", fg="#ECF0F1", font=("Segoe UI", 11, "bold"))
            local_label.pack(pady=(0,6))
            local_bar = ttk.Progressbar(local_inner, mode='determinate', length=300)
            local_bar.pack()
            try:
                total = max(1, len(new_listings))
                local_bar.configure(maximum=total, value=0)
            except Exception:
                total = len(new_listings)

            # Clear current rows
            for item in tree.get_children():
                tree.delete(item)
            try:
                all_row_ids.clear()
            except Exception:
                pass

            # Reset results cache
            try:
                results_cache.clear()
            except Exception:
                pass

            # Recompute header (listings count)
            try:
                header_text_var.set(f"📍 Address Match ({len(new_listings)} listings • API calls: {api_calls_count.get()})")
            except Exception:
                pass

            # Get DB connection for prefetch (reuse shared connection)
            db_conn2 = get_db_connection()
            db_cursor2 = None
            if db_conn2:
                try:
                    db_cursor2 = db_conn2.cursor(buffered=True)
                except Exception as _e:
                    log_to_file(f"[Address Match] Refresh cursor failed: {_e}")
                    db_cursor2 = None
            else:
                log_to_file(f"[Address Match] Refresh DB connect failed")

            # Populate rows with ETA like initial load
            t0 = time.time()
            def _fmt_secs(sec: float) -> str:
                sec = max(0, int(sec))
                m, s = divmod(sec, 60)
                return f"{m:02d}:{s:02d}"

            for i, listing in enumerate(new_listings, 1):
                try:
                    google_address = listing.get("google_address", "N/A")
                    json_google_addresses_id = listing.get("google_addresses_id", "")
                    json_google_places_id = listing.get("google_places_id", "")
                    king_county_id = listing.get("king_county_id", "")
                    apartment_listing_id = (
                        listing.get("id")
                        or listing.get("apartment_listings_id")
                        or listing.get("apartment_id")
                        or listing.get("apt_id")
                        or ""
                    )

                    # Resolve Apt ID if missing
                    if (not apartment_listing_id) and db_cursor2 is not None:
                        try:
                            listing_website = listing.get("listing_website") or listing.get("url") or listing.get("link")
                            full_address = listing.get("full_address") or listing.get("address")
                            if listing_website:
                                db_cursor2.execute("SELECT id FROM apartment_listings WHERE listing_website = %s LIMIT 1", (listing_website,))
                                row = db_cursor2.fetchone()
                                if row and row[0]:
                                    apartment_listing_id = row[0]
                            if (not apartment_listing_id) and full_address:
                                db_cursor2.execute("SELECT id FROM apartment_listings WHERE full_address = %s LIMIT 1", (full_address,))
                                row = db_cursor2.fetchone()
                                if row and row[0]:
                                    apartment_listing_id = row[0]
                        except Exception as e:
                            log_to_file(f"[Address Match] Refresh AptID prefetch failed row {i}: {e}")

                    # Prefetch preloaded GA/GP
                    preloaded_ga_id = ""
                    preloaded_gp_id = ""
                    if apartment_listing_id and db_cursor2 is not None:
                        try:
                            db_cursor2.execute(
                                "SELECT google_addresses_id, google_places_id FROM apartment_listings WHERE id = %s LIMIT 1",
                                (apartment_listing_id,)
                            )
                            row = db_cursor2.fetchone()
                            if row:
                                db_ga_id, db_gp_id = row
                                if db_ga_id is not None and str(db_ga_id).strip() != "":
                                    preloaded_ga_id = db_ga_id
                                if db_gp_id is not None and str(db_gp_id).strip() != "":
                                    preloaded_gp_id = db_gp_id
                        except Exception as e:
                            log_to_file(f"[Address Match] Refresh prefetch GA/GP failed id {apartment_listing_id}: {e}")

                    # Placeholders for fields filled after API run
                    name = "-"; rating = "-"; reviews = "-"; formatted_addr = "-"

                    zebra_tag = "odd" if (i % 2 == 1) else "even"
                    preloaded_display = f"{preloaded_ga_id} 🗑" if preloaded_ga_id else "-"
                    rid = tree.insert("", "end", values=(
                        i,
                        apartment_listing_id if apartment_listing_id else "-",
                        preloaded_display,
                        google_address,
                        formatted_addr,
                        name,
                        rating,
                        reviews,
                        str(preloaded_ga_id) if preloaded_ga_id else "-",
                        json_google_places_id if json_google_places_id else "-",
                        king_county_id if king_county_id else "-",
                        "-",  # Score
                        "-",  # Type
                        "-",  # GAPI
                        "▶"   # Play button
                    ), tags=(zebra_tag,))
                    try:
                        all_row_ids.append(rid)
                    except Exception:
                        pass

                    # Update progress/ETA
                    try:
                        elapsed = time.time() - t0
                        avg = (elapsed / i) if i > 0 else 0
                        remaining = max(0.0, (total - i) * avg)
                        pct = int((i / total) * 100) if total > 0 else 100
                        local_bar.configure(value=i)
                        local_label.config(text=f"Refreshing listings… {i}/{total} ({pct}%) • elapsed {_fmt_secs(elapsed)} • ETA {_fmt_secs(remaining)}")
                        window.update_idletasks()
                    except Exception:
                        pass
                except Exception as row_err:
                    log_to_file(f"[Address Match] Refresh insert row error: {row_err}")

            # Close DB cursor (but keep shared connection alive)
            try:
                if db_cursor2 is not None:
                    db_cursor2.close()
                # Don't close shared connection
            except Exception:
                pass

            # Hide overlay
            try:
                local_overlay.place_forget()
                local_overlay.destroy()
            except Exception:
                pass

            # Recompute API calls tally (will be 0 after refresh)
            try:
                refresh_api_calls_tally()
            except Exception:
                pass
            
            # Update statistics and apply unified filters
            try:
                update_statistics()
                recompute_row_visibility()
            except Exception:
                pass
        except Exception as e:
            log_to_file(f"[Address Match] Refresh failed: {e}")

    # Refresh button
    tk.Button(
        btn_frame,
        text="Refresh",
        command=refresh_table,
        bg="#3498DB",
        fg="#fff",
        font=("Segoe UI", 10, "bold"),
        relief="flat",
        padx=14,
        pady=5,
        cursor="hand2"
    ).pack(side="left", padx=10)

    # Auto-update checkbox
    auto_update_var = tk.BooleanVar(master=window, value=False)
    auto_update_check = tk.Checkbutton(
        btn_frame,
        text="Auto Update",
        variable=auto_update_var,
        command=toggle_auto_update,
        bg="#1E1E1E",
        fg="#ECF0F1",
        selectcolor="#2C3E50",
        font=("Segoe UI", 10, "bold"),
        activebackground="#1E1E1E",
        activeforeground="#3498DB",
        cursor="hand2"
    )
    auto_update_check.pack(side="left", padx=10)
    
    # Show No Apt ID checkbox
    show_no_apt_id_var = tk.BooleanVar(master=window, value=False)
    def toggle_show_no_apt_id():
        """Bridge legacy 'Show No Apt ID' checkbox to unified filters."""
        try:
            want_show_empty = bool(show_no_apt_id_var.get())
            filter_no_apt_id_var.set(want_show_empty)
            # If explicitly showing empty Apt ID, keep 'Has Apt ID' as-is; otherwise unchanged
            recompute_row_visibility()
        except Exception:
            pass
    
    show_no_apt_id_check = tk.Checkbutton(
        btn_frame,
        text="Show No Apt ID",
        variable=show_no_apt_id_var,
        command=toggle_show_no_apt_id,
        bg="#1E1E1E",
        fg="#ECF0F1",
        selectcolor="#2C3E50",
        font=("Segoe UI", 10, "bold"),
        activebackground="#1E1E1E",
        activeforeground="#3498DB",
        cursor="hand2"
    )
    show_no_apt_id_check.pack(side="left", padx=10)
    
    def on_window_close():
        """Clean up resources before closing window."""
        close_db_connection()
        window.destroy()
    
    tk.Button(btn_frame, text="Close", command=on_window_close,
              bg="#95A5A6", fg="#fff", font=("Segoe UI", 9), 
              relief="flat", padx=15, pady=5, cursor="hand2").pack(side="left", padx=5)
    
    # Also bind window close event (X button)
    window.protocol("WM_DELETE_WINDOW", on_window_close)

def show_insert_db_window(job_id, parent, table=None):
    """
    Display a window showing real-time progress for inserting/updating apartment listings in the database.
    Shows: estimate to finish, listings as they're processed, and stats for new/changed/inactive listings.
    """
    log_to_file(f"[Insert DB] Window function called for job {job_id}")
    
    from tkinter import ttk, messagebox
    
    try:
        import mysql.connector
    except ImportError:
        messagebox.showerror("Error", "mysql-connector-python is not installed. Please install it with:\npip install mysql-connector-python", parent=parent)
        log_to_file(f"[Insert DB] mysql-connector-python not installed")
        return
    
    # Find JSON file for this job - check both Networks and Websites subfolders
    log_to_file(f"[Insert DB] Looking for JSON file for job {job_id}")
    date_str = datetime.now().strftime("%Y-%m-%d")
    
    # Try Networks folder first (networks_X.json)
    json_path = BASE_DIR / date_str / "Networks" / f"networks_{job_id}.json"
    log_to_file(f"[Insert DB] Initial path: {json_path}")
    
    # If not found, try Websites folder (google_places_X.json)
    if not json_path.exists():
        json_path = BASE_DIR / date_str / "Websites" / f"google_places_{job_id}.json"
        log_to_file(f"[Insert DB] Not in Networks, trying Websites: {json_path}")
    
    # Search all date folders if not found today
    if not json_path.exists():
        log_to_file(f"[Insert DB] File not found at {json_path}, searching other folders...")
        # Search both Networks and Websites folders
        pattern1 = str(BASE_DIR / "*" / "Networks" / f"networks_{job_id}.json")
        pattern2 = str(BASE_DIR / "*" / "Websites" / f"google_places_{job_id}.json")
        matching = __import__('glob').glob(pattern1) + __import__('glob').glob(pattern2)
        log_to_file(f"[Insert DB] Found {len(matching)} matching files")
        if matching:
            json_path = Path(max(matching, key=lambda p: os.path.getmtime(p)))
            log_to_file(f"[Insert DB] Using: {json_path}")
        else:
            log_to_file(f"[Insert DB] No JSON file found for job {job_id}")
            messagebox.showerror("Error", f"No JSON file found for job {job_id}", parent=parent)
            return
    else:
        log_to_file(f"[Insert DB] Found JSON at: {json_path}")
    
    # Load JSON
    log_to_file(f"[Insert DB] Loading JSON from {json_path}...")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            listings = json.load(f)
        log_to_file(f"[Insert DB] Loaded {len(listings)} listings from JSON")
    except Exception as e:
        log_to_file(f"[Insert DB] Failed to load JSON: {e}")
        log_to_file(f"[Insert DB] Failed to load JSON: {e}")
        messagebox.showerror("Error", f"Failed to load JSON: {e}", parent=parent)
        return
    
    if not listings:
        log_to_file(f"[Insert DB] No listings found in JSON file")
        messagebox.showinfo("Info", "No listings found in JSON file.", parent=parent)
        return
    
    # Create window with activity window style
    log_to_file(f"[Insert DB] Creating window...")
    
    # Get screen dimensions and calculate 20% width
    screen_width = parent.winfo_screenwidth()
    window_width = int(screen_width * 0.20)  # 20% of screen width
    window_height = parent.winfo_screenheight() - 100  # Nearly full height
    
    # Position below the Activity Window (assuming Activity Window is at top-left)
    # Activity Window height is approximately screen_height - 100, so position this to the right or below
    x_position = window_width + 10  # Position to the right of Activity Window with 10px gap
    y_position = 0  # Same top position
    
    window = tk.Toplevel(parent)
    window.title(f"Job {job_id} - Step 5: Insert DB")
    window.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
    window.configure(bg="#1e1e1e")
    window.attributes('-topmost', True)
    log_to_file(f"[Insert DB] Window created successfully")
    
    # Main container
    main_frame = tk.Frame(window, bg="#1e1e1e")
    main_frame.pack(fill="both", expand=True)
    
    # Stats frame (compact for narrow window)
    stats_frame = tk.Frame(main_frame, bg="#1e1e1e")
    stats_frame.pack(pady=10, padx=10, fill="x")
    
    # Stats variables - IMPORTANT: must specify master=window
    new_count_var = tk.StringVar(master=window, value="New: 0")
    price_change_var = tk.StringVar(master=window, value="Price ∆: 0")
    inactive_count_var = tk.StringVar(master=window, value="Inactive: 0")
    total_var = tk.StringVar(master=window, value=f"0/{len(listings)}")
    eta_var = tk.StringVar(master=window, value="Calculating...")
    
    # Stats labels (stacked vertically for narrow window)
    tk.Label(stats_frame, textvariable=new_count_var, bg="#1e1e1e", fg="#2ECC71", 
             font=("Consolas", 8, "bold")).pack(fill="x", pady=1)
    tk.Label(stats_frame, textvariable=price_change_var, bg="#1e1e1e", fg="#F39C12", 
             font=("Consolas", 8, "bold")).pack(fill="x", pady=1)
    tk.Label(stats_frame, textvariable=inactive_count_var, bg="#1e1e1e", fg="#E74C3C", 
             font=("Consolas", 8, "bold")).pack(fill="x", pady=1)
    
    # Progress frame
    progress_frame = tk.Frame(main_frame, bg="#1e1e1e")
    progress_frame.pack(pady=5, padx=10, fill="x")
    
    tk.Label(progress_frame, textvariable=total_var, bg="#1e1e1e", fg="#ECF0F1", 
             font=("Consolas", 7)).pack(fill="x")
    tk.Label(progress_frame, textvariable=eta_var, bg="#1e1e1e", fg="#3498DB", 
             font=("Consolas", 7)).pack(fill="x")
    
    # Progress bar (adjusted width)
    progress_bar = ttk.Progressbar(main_frame, length=window_width-40, mode='determinate', maximum=len(listings))
    progress_bar.pack(pady=5, padx=10)
    
    # Separator
    sep = tk.Frame(main_frame, height=2, bg="#444")
    sep.pack(fill="x", padx=10, pady=5)
    
    # Activity window label
    activity_label = tk.Label(main_frame, text="Activity Window", font=("Arial", 9, "bold"), bg="#1e1e1e", fg="#fff")
    activity_label.pack(pady=(5,5))
    
    # Listings display (scrollable text widget) - activity window style
    list_frame = tk.Frame(main_frame, bg="#1e1e1e")
    list_frame.pack(pady=5, padx=10, fill="both", expand=True)
    
    scrollbar = tk.Scrollbar(list_frame)
    scrollbar.pack(side="right", fill="y")
    
    text_widget = tk.Text(list_frame, bg="#0d0d0d", fg="#00ff00", font=("Consolas", 8),
                          yscrollcommand=scrollbar.set, wrap="word", state="disabled", 
                          relief="flat", padx=6, pady=6)
    text_widget.pack(side="left", fill="both", expand=True)
    scrollbar.config(command=text_widget.yview)
    
    # Close button
    tk.Button(main_frame, text="Close", command=window.destroy,
              bg="#2d2d2d", fg="#fff", font=("Consolas", 8), 
              relief="flat", padx=10, pady=3, cursor="hand2").pack(pady=10)
    
    # --- Thread-safe UI helpers ---
    def ui_append(line: str):
        def _do():
            text_widget.config(state="normal")
            text_widget.insert("end", line if line.endswith("\n") else line + "\n")
            text_widget.see("end")
            text_widget.config(state="disabled")
        window.after(0, _do)

    def ui_set_stats(new_count=None, price_changes=None, total=None, inactive=None):
        def _do():
            if new_count is not None:
                new_count_var.set(f"New: {new_count}")
            if price_changes is not None:
                price_change_var.set(f"Price ∆: {price_changes}")
            if inactive is not None:
                inactive_count_var.set(f"Inactive: {inactive}")
            if total is not None:
                total_var.set(total)
        window.after(0, _do)

    def ui_set_eta(seconds_text: str):
        window.after(0, lambda: eta_var.set(seconds_text))

    def ui_set_progress(val: int):
        window.after(0, lambda: progress_bar.configure(value=val))

    # Processing logic
    def process_listings():
        """Process all listings and update the database."""
        new_count = 0
        price_change_count = 0
        inactive_count = 0
        processed = 0
        start_time = time.time()
        
        try:
            log_to_file(f"[Insert DB] Starting to process {len(listings)} listings")
            # Show initial status in the window
            ui_append(f"Processing {len(listings)} listings...")
            ui_append("Connecting to database...")

            # Connect to database with retries
            max_attempts = 3
            last_err = None
            conn = None
            cursor = None
            for attempt in range(1, max_attempts + 1):
                try:
                    log_to_file(f"[Insert DB] Connecting to database (10s timeout)... attempt {attempt}/{max_attempts}")
                    ui_append(f"Connecting to database... (attempt {attempt}/{max_attempts})")
                    conn = mysql.connector.connect(
                        host='localhost',
                        user='local_uzr',
                        password='fuck',
                        database='offta',
                        port=3306,
                        connection_timeout=10,
                        use_pure=True
                    )
                    try:
                        conn.autocommit = True
                    except Exception:
                        pass

                    cursor = conn.cursor(buffered=True)
                    cursor.execute("SELECT 1")
                    _ = cursor.fetchone()
                    log_to_file(f"[Insert DB] Database connected successfully")
                    ui_append("Connected! Starting inserts...\n")
                    break
                except Exception as ce:
                    last_err = ce
                    log_to_file(f"[Insert DB] DB connect failed: {ce}")
                    ui_append(f"❌ DB connect failed: {ce}")
                    if attempt < max_attempts:
                        time.sleep(2 * attempt)
            if cursor is None:
                raise Exception(f"Database connection failed after {max_attempts} attempts: {last_err}")
            
            # Helper: normalize image URLs to a single comma-separated string
            def norm_img_urls(value):
                if isinstance(value, list):
                    return ",".join([str(x).strip() for x in value if str(x).strip()])
                return str(value or "").strip()

            # Helper: parse available_date into YYYY-MM-DD if possible, else None
            def parse_available_date(val):
                if not val:
                    return None
                s = str(val).strip()
                sl = s.lower()
                if sl in ("now", "today", "available now", "immediate"):
                    return None
                for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%m-%d-%Y", "%m-%d-%y"):
                    try:
                        return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
                    except Exception:
                        continue
                return None

            # Helper: parse integer from various string formats like "$1,750" or "1,200 sqft"
            def to_int(val, default=0):
                try:
                    if val is None:
                        return default
                    if isinstance(val, (int,)):
                        return int(val)
                    if isinstance(val, float):
                        return int(round(val))
                    s = str(val)
                    digits = ''.join(ch for ch in s if ch.isdigit())
                    return int(digits) if digits else default
                except Exception:
                    return default

            # Helper: parse float from strings like "1.5 bath" or "2"
            def to_float(val, default=0.0):
                try:
                    if val is None:
                        return default
                    if isinstance(val, (int, float)):
                        return float(val)
                    s = str(val)
                    # Keep digits and dot
                    cleaned = ''.join(ch for ch in s if (ch.isdigit() or ch == '.'))
                    return float(cleaned) if cleaned else default
                except Exception:
                    return default

            # Helper: return numeric string (for VARCHAR columns) preserving decimals when requested
            def to_num_str(val, allow_decimal: bool = False, default: str = "0") -> str:
                try:
                    if val is None:
                        return default
                    s = str(val)
                    if allow_decimal:
                        cleaned = ''.join(ch for ch in s if (ch.isdigit() or ch == '.'))
                        # Normalize multiple dots
                        parts = cleaned.split('.')
                        if len(parts) > 2:
                            cleaned = parts[0] + '.' + ''.join(parts[1:])
                        return cleaned if cleaned else default
                    else:
                        digits = ''.join(ch for ch in s if ch.isdigit())
                        return digits if digits else default
                except Exception:
                    return default

            # Track current keys for deactivation
            current_urls = set()
            current_full_addresses = set()
            current_domains = set()

            for i, listing in enumerate(listings, 1):
                # Extract listing data from JSON
                full_address = listing.get("full_address") or listing.get("address") or ""
                price = to_int(listing.get("price"), 0)  # INT column in DB
                bedrooms = to_num_str(listing.get("bedrooms"), allow_decimal=False, default="0")  # VARCHAR(100)
                bathrooms = to_num_str(listing.get("bathrooms"), allow_decimal=True, default="0")   # VARCHAR(100), keep 1.5
                sqft = to_num_str(listing.get("sqft"), allow_decimal=False, default="0")            # VARCHAR(50)
                description = listing.get("description") or ""
                img_urls = norm_img_urls(listing.get("img_urls") or listing.get("img_url") or "")
                available = listing.get("available") or ""
                available_date = parse_available_date(listing.get("available_date"))
                building_name = listing.get("building_name") or listing.get("Building_Name") or None
                city = listing.get("city") or None
                state = listing.get("state") or None
                listing_website = listing.get("listing_website") or listing.get("url") or listing.get("link") or None
                listing_id_from_json = listing.get("listing_id") or None

                # Track keys for later deactivation within same source domain
                if listing_website:
                    try:
                        from urllib.parse import urlparse as _urlparse
                        dom = _urlparse(listing_website).netloc
                        if dom:
                            current_domains.add(dom)
                    except Exception:
                        pass
                    current_urls.add(listing_website)
                if full_address:
                    current_full_addresses.add(full_address)

                # Determine network id from JSON or fallback to job id
                try:
                    this_network_id = int(listing.get("network_id") or int(job_id))
                except Exception:
                    this_network_id = int(job_id)

                # Determine lookup strategy: prefer listing_website, fallback to full_address
                existing = None
                if listing_website:
                    cursor.execute("SELECT id, price, active FROM apartment_listings WHERE listing_website = %s", (listing_website,))
                    existing = cursor.fetchone()
                if not existing and full_address:
                    cursor.execute("SELECT id, price, active FROM apartment_listings WHERE full_address = %s", (full_address,))
                    existing = cursor.fetchone()

                if existing:
                    listing_id, old_price, _active = existing

                    # Price change detection (persist to history table and UI)
                    if (old_price or 0) != (price or 0):
                        try:
                            change_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            cursor.execute(
                                """
                                INSERT INTO apartment_listings_price_changes
                                (apartment_listings_id, new_price, time)
                                VALUES (%s, %s, %s)
                                """,
                                (listing_id, str(price), change_time)
                            )
                            
                            # Track in network_daily_stats
                            try:
                                today = datetime.now().strftime('%Y-%m-%d')
                                cursor.execute("""
                                    INSERT INTO network_daily_stats 
                                    (network_id, date, price_changes, apartments_added, apartments_subtracted, total_listings)
                                    VALUES (%s, %s, 1, 0, 0, 0)
                                    ON DUPLICATE KEY UPDATE 
                                    price_changes = price_changes + 1
                                """, (this_network_id, today))
                            except Exception as stats_err:
                                log_to_file(f"[Insert DB] network_daily_stats update failed: {stats_err}")
                        except Exception as pc_err:
                            log_to_file(f"[Insert DB] Price change insert failed for id {listing_id}: {pc_err}")
                        price_change_count += 1
                        status = f"💰 PRICE CHANGE: {(full_address or listing_website)[:60]} ({old_price} → {price})"
                    else:
                        status = f"✓ UPDATED: {(full_address or listing_website)[:60]}"

                    # Update all fields except price (price is constant)
                    cursor.execute(
                        """
                        UPDATE apartment_listings
                        SET bedrooms=%s, bathrooms=%s, sqft=%s,
                            description=%s, img_urls=%s, available=%s, available_date=%s,
                            time_updated=NOW(), active='yes', network_id=%s, listing_id=%s
                        WHERE id=%s
                        """,
                        (bedrooms, bathrooms, sqft, description, img_urls, available, available_date, this_network_id, listing_id_from_json, listing_id)
                    )
                else:
                    # Insert new listing (minimal, using existing schema columns)
                    cursor.execute(
                        """
                        INSERT INTO apartment_listings
                        (active, bedrooms, bathrooms, sqft, price, img_urls, available, available_date,
                         description, Building_Name, full_address, city, state, listing_website,
                         time_created, time_updated, network_id, listing_id)
                        VALUES ('yes', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s)
                        """,
                        (bedrooms, bathrooms, sqft, price, img_urls, available, available_date,
                         description, building_name, full_address, city, state, listing_website, this_network_id, listing_id_from_json)
                    )
                    new_count += 1
                    status = f"✨ NEW: {(full_address or listing_website or 'unknown')[:60]} ({price})"
                    
                    # Track new listing in network_daily_stats
                    try:
                        today = datetime.now().strftime('%Y-%m-%d')
                        cursor.execute("""
                            INSERT INTO network_daily_stats 
                            (network_id, date, price_changes, apartments_added, apartments_subtracted, total_listings)
                            VALUES (%s, %s, 0, 1, 0, 0)
                            ON DUPLICATE KEY UPDATE 
                            apartments_added = apartments_added + 1
                        """, (this_network_id, today))
                    except Exception as stats_err:
                        log_to_file(f"[Insert DB] network_daily_stats new listing update failed: {stats_err}")

                conn.commit()
                processed += 1

                # Update UI
                ui_append(status)

                # Update stats
                ui_set_stats(new_count=new_count, price_changes=price_change_count, total=f"{processed}/{len(listings)}")
                ui_set_progress(processed)

                # Calculate ETA
                elapsed = time.time() - start_time
                if processed > 0:
                    avg_time = elapsed / processed
                    remaining = len(listings) - processed
                    eta_seconds = avg_time * remaining
                    ui_set_eta(f"~{int(eta_seconds)}s left")

            # Mark inactive listings for this network_id (network_xx):
            # Any active row with the same network_id as current job but not present in this JSON becomes inactive.
            log_to_file(f"[Insert DB] ⚠️ CHECKPOINT 1: About to check inactive listings for network {job_id}")
            ui_append(f"⚠️ Checking inactive listings for network {job_id}...")
            try:
                cursor.execute(
                    "SELECT id, listing_website, full_address FROM apartment_listings WHERE active='yes' AND network_id=%s",
                    (int(job_id),)
                )
                rows = cursor.fetchall() or []
                deactivated_here = 0
                for lid, url, fa in rows:
                    present = False
                    if url and url in current_urls:
                        present = True
                    elif fa and fa in current_full_addresses:
                        present = True
                    if not present:
                        cursor.execute("UPDATE apartment_listings SET active='no', time_updated=NOW() WHERE id=%s", (lid,))
                        inactive_count += 1
                        deactivated_here += 1
                
                # Track removed listings in network_daily_stats
                if deactivated_here > 0:
                    try:
                        today = datetime.now().strftime('%Y-%m-%d')
                        cursor.execute("""
                            INSERT INTO network_daily_stats 
                            (network_id, date, price_changes, apartments_added, apartments_subtracted, total_listings)
                            VALUES (%s, %s, 0, 0, %s, 0)
                            ON DUPLICATE KEY UPDATE 
                            apartments_subtracted = apartments_subtracted + %s
                        """, (int(job_id), today, deactivated_here, deactivated_here))
                    except Exception as stats_err:
                        log_to_file(f"[Insert DB] network_daily_stats removal update failed: {stats_err}")
                
                conn.commit()
                log_to_file(f"[Insert DB] ⚠️ CHECKPOINT 2: Committed deactivation changes. Deactivated: {deactivated_here}")
                ui_append(f"🧹 Marked {deactivated_here} listing(s) inactive for network_{job_id}")
            except Exception as deact_err:
                log_to_file(f"[Insert DB] Network-based deactivation failed for network_id={job_id}: {deact_err}")

            log_to_file(f"[Insert DB] ⚠️ CHECKPOINT 3: Setting final UI stats and ETA")
            ui_set_stats(inactive=inactive_count)
            ui_set_eta("Done!")
            
            # Write final stats to network_daily_stats for TODAY
            # If a row exists for this network_id + date, REPLACE the values with this run's totals
            log_to_file(f"[Insert DB] ⚠️ ABOUT TO WRITE STATS: network={job_id}, today={datetime.now().strftime('%Y-%m-%d')}, price_changes={price_change_count}, new={new_count}, removed={inactive_count}, total={processed}")
            try:
                today = datetime.now().strftime('%Y-%m-%d')
                log_to_file(f"[Insert DB] Writing final stats to network_daily_stats for network {job_id} on {today}: price_changes={price_change_count}, new={new_count}, removed={inactive_count}")
                cursor.execute("""
                    INSERT INTO network_daily_stats 
                    (network_id, date, price_changes, apartments_added, apartments_subtracted, total_listings)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE 
                    price_changes = %s,
                    apartments_added = %s,
                    apartments_subtracted = %s,
                    total_listings = %s
                """, (int(job_id), today, price_change_count, new_count, inactive_count, processed,
                      price_change_count, new_count, inactive_count, processed))
                conn.commit()
                log_to_file(f"[Insert DB] ✅ Successfully wrote stats for network {job_id} - affected rows: {cursor.rowcount}")
                log_to_file(f"[Insert DB] ⚠️ CHECKPOINT 4: Stats INSERT completed successfully")
            except Exception as final_stats_err:
                log_to_file(f"[Insert DB] ❌ FAILED to write final stats for network {job_id}: {final_stats_err}")
                log_exception("Stats INSERT failed")
            
            cursor.close()
            conn.close()
            
            log_to_file(f"[Insert DB] Job {job_id}: {new_count} new, {price_change_count} price changes, {inactive_count} inactive")
            
            # Show completion message
            ui_append("\n" + "="*60)
            ui_append("✅ COMPLETE!")
            ui_append("="*60)
            
        except Exception as e:
            error_msg = f"Error processing listings:\n{str(e)}"
            log_to_file(f"[Insert DB Error] Job {job_id}: {error_msg}")
            log_exception("Insert DB processing error")
            
            # Show error in window
            ui_append(f"\n❌ ERROR: {error_msg}")
            # Update title to reflect error instead of showing modal dialog
            window.after(0, lambda: window.title(f"Insert DB - Error (Job {job_id})"))
    
    # Helper to mark step status via API when finished
    def mark_step_status(status: str, message: str):
        if not table:
            return
        try:
            api_url = php_url("queue_step_api.php")
            payload = {
                'table': table,
                'id': job_id,
                'step': 'insert_db',
                'status': status,
                'message': message,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            requests.post(api_url, json=payload, timeout=5)
            log_to_file(f"[Insert DB] Marked step {status} via API for job {job_id}")
        except Exception as e:
            log_to_file(f"[Insert DB] Failed to mark step status: {e}")

    # Wrap processing to mark completion
    def run_with_completion():
        ok = True
        try:
            log_to_file(f"[Insert DB] Starting run_with_completion thread for job {job_id}")
            process_listings()
            log_to_file(f"[Insert DB] process_listings completed successfully for job {job_id}")
        except Exception as thread_err:
            ok = False
            log_to_file(f"[Insert DB] Exception in run_with_completion: {thread_err}")
            log_exception("run_with_completion error")
            # Show error in UI
            ui_append(f"\n❌ THREAD ERROR: {thread_err}")
        finally:
            if ok:
                mark_step_status('done', 'completed')
            else:
                mark_step_status('error', 'failed')
            log_to_file(f"[Insert DB] run_with_completion finished for job {job_id}, ok={ok}")

        # Start processing in background thread
        try:
            log_to_file(f"[Insert DB] Creating background thread for job {job_id}")
            t = threading.Thread(target=run_with_completion, daemon=True)
            t.start()
            log_to_file(f"[Insert DB] Background thread started successfully for job {job_id}")
        except Exception as start_err:
            log_to_file(f"[Insert DB] Failed to start thread: {start_err}")
            log_exception("Thread start error")
            ui_append(f"\n❌ Failed to start processing thread: {start_err}")

