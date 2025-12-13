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
                        host='172.104.206.182',
                        user='seattlelisted_usr',
                        password='T@5z6^pl}',
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

