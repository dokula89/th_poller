#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session management and login dialog
Extracted from config_utils.py (lines 69-477)
"""

from config_core import *

# Simple local session for login persistence (24h)
# ----------------------------
SESSION_FILE = Path(__file__).parent / ".queue_poller_session.json"

def _save_session(username: str, expires_ts: float):
    try:
        data = {"user": username, "expires": float(expires_ts)}
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f)
        log_to_file(f"[Auth] Session saved for user '{username}', expires {datetime.fromtimestamp(expires_ts)}")
    except Exception as e:
        log_to_file(f"[Auth] Failed to save session: {e}")

def _load_session() -> Optional[dict]:
    try:
        if SESSION_FILE.exists():
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log_to_file(f"[Auth] Failed to load session: {e}")
    return None

def _clear_session():
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
            log_to_file("[Auth] Session cleared")
    except Exception as e:
        log_to_file(f"[Auth] Failed to clear session: {e}")

def _session_valid() -> bool:
    try:
        data = _load_session()
        if not data:
            return False
        exp = float(data.get("expires", 0))
        now = time.time()
        if now < exp and data.get("user") == "daniel":
            return True
    except Exception as e:
        log_to_file(f"[Auth] Session validation error: {e}")
    return False

# ----------------------------
# Login helpers usable before HUD
# ----------------------------
def show_login_dialog(parent_root) -> bool:
    """Show a modal login dialog on the given Tk root. Returns True if signed in."""
    try:
        if _session_valid():
            log_to_file("[Auth] Existing valid session; no login needed")
            return True

        log_to_file("[Auth] Creating login dialog window")
        
        # Allow forcing standalone login window (env var): LOGIN_STANDALONE=1
        is_standalone = bool(os.environ.get("LOGIN_STANDALONE"))

        # Temporarily show parent if hidden (needed for Toplevel to appear)
        parent_was_hidden = False
        if not is_standalone:
            try:
                if parent_root.state() == 'withdrawn':
                    parent_was_hidden = True
                    parent_root.deiconify()
                    parent_root.update()
                    log_to_file("[Auth] Parent was hidden, temporarily showing")
            except Exception as e:
                log_to_file(f"[Auth] Error checking parent state: {e}")
        
        win = tk.Tk() if is_standalone else tk.Toplevel(parent_root)
        log_to_file("[Auth] Toplevel created")
        win.title("Sign in")
        # Center the dialog on screen
        try:
            w, h = 340, 240
            sw = win.winfo_screenwidth()
            sh = win.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            win.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            win.geometry("340x240")
        try:
            win.resizable(False, False)
        except Exception:
            pass
        
        # Don't set transient or grab yet - wait until window is configured
        
        try:
            win.attributes('-topmost', True)
            win.lift()
            win.focus_force()
        except Exception:
            pass

        bg2 = "#0D1117"; fg2 = "#E8EAED"; accent2 = "#238636"
        win.configure(bg=bg2)
        cont = tk.Frame(win, bg=bg2)
        cont.pack(fill="both", expand=True, padx=16, pady=16)

        title_lbl = tk.Label(cont, text="Queue Poller Login", fg=fg2, bg=bg2, font=("Segoe UI", 13, "bold"))
        title_lbl.pack(pady=(0,12))

        # Username
        u_row = tk.Frame(cont, bg=bg2); u_row.pack(fill="x", pady=(2,2))
        tk.Label(u_row, text="Username", fg=fg2, bg=bg2, font=("Segoe UI", 9)).pack(anchor="w")
        u_var = tk.StringVar(value="daniel")
        u_ent = tk.Entry(u_row, textvariable=u_var); u_ent.pack(fill="x")

        # Password
        p_row = tk.Frame(cont, bg=bg2); p_row.pack(fill="x", pady=(6,2))
        tk.Label(p_row, text="Password", fg=fg2, bg=bg2, font=("Segoe UI", 9)).pack(anchor="w")
        p_var = tk.StringVar(value="Teller89*")
        p_ent = tk.Entry(p_row, textvariable=p_var, show="*"); p_ent.pack(fill="x")

        # Stay logged in checkbox
        stay_logged_in = tk.IntVar(value=1)  # Default checked
        check_row = tk.Frame(cont, bg=bg2); check_row.pack(fill="x", pady=(8,0))
        tk.Checkbutton(
            check_row, 
            text="Stay logged in for 24 hours", 
            variable=stay_logged_in,
            fg=fg2, 
            bg=bg2,
            selectcolor=bg2,
            activebackground=bg2,
            activeforeground=fg2,
            font=("Segoe UI", 9)
        ).pack(anchor="w")

        # Error label
        err_var = tk.StringVar(value="")
        err_lbl = tk.Label(cont, textvariable=err_var, fg="#E74C3C", bg=bg2, font=("Segoe UI", 8))
        err_lbl.pack(fill="x", pady=(4,0))

        result = {"ok": False}
        def do_login():
            username = (u_var.get() or "").strip()
            password = p_var.get() or ""
            if username == "daniel" and password == "Teller89*":
                # Use checkbox to determine session length
                if stay_logged_in.get():
                    expires = time.time() + 24*60*60  # 24 hours
                else:
                    expires = time.time() + 60*60  # 1 hour
                _save_session(username, expires)
                result["ok"] = True
                try:
                    win.grab_release()
                except Exception:
                    pass
                win.destroy()
            else:
                err_var.set("Invalid credentials. Try again.")
                log_to_file("[Auth] Login failed: invalid credentials")

        def do_cancel():
            result["ok"] = False
            try:
                win.grab_release()
            except Exception:
                pass
            win.destroy()

        # Buttons
        btn_row = tk.Frame(cont, bg=bg2); btn_row.pack(fill="x", pady=(12,0))
        login_btn = tk.Button(
            btn_row, 
            text="Sign In", 
            command=do_login, 
            bg=accent2, 
            fg="#FFFFFF", 
            font=("Segoe UI", 10, "bold"), 
            relief="flat", 
            padx=20, 
            pady=6, 
            cursor="hand2",
            borderwidth=0
        )
        login_btn.pack(side="right")
        
        cancel_btn = tk.Button(
            btn_row, 
            text="Cancel", 
            command=do_cancel, 
            bg="#6C757D", 
            fg="#FFFFFF", 
            font=("Segoe UI", 10), 
            relief="flat", 
            padx=16, 
            pady=6, 
            cursor="hand2",
            borderwidth=0
        )
        cancel_btn.pack(side="right", padx=(0,10))

        # Binds/focus
        u_ent.bind("<Return>", lambda _e: p_ent.focus_set())
        p_ent.bind("<Return>", lambda _e: do_login())
        
        # Force window to appear and update
        try:
            # Ensure it's not minimized and is mapped
            try:
                win.state('normal')
                win.deiconify()
            except Exception:
                pass

            # Wait until the window is visible to the window manager
            try:
                win.wait_visibility()
                log_to_file("[Auth] Login dialog is visible to WM")
            except Exception:
                pass

            # Repeatedly raise and focus the window for the first ~1s
            def _force_front(attempt: int = 0):
                try:
                    win.deiconify()
                    win.lift()
                    win.focus_force()
                    win.attributes('-topmost', True)
                    win.update_idletasks()
                    win.update()
                except Exception as e2:
                    log_to_file(f"[Auth] force_front error: {e2}")
                finally:
                    if attempt < 6:
                        # Try again a few times (helps with focus-stealing protections)
                        try:
                            win.after(150, lambda: _force_front(attempt + 1))
                        except Exception:
                            pass
                    elif attempt == 6:
                        # Drop topmost after we brought it to front
                        try:
                            win.attributes('-topmost', False)
                        except Exception:
                            pass

            _force_front(0)

            # When window gains focus, drop topmost
            try:
                win.bind("<FocusIn>", lambda _e: win.attributes('-topmost', False))
            except Exception:
                pass

            # Nudge geometry in case of odd DPI/multi-monitor placement
            try:
                win.after(350, lambda: win.geometry("+100+100"))
                win.after(700, lambda: win.lift())
            except Exception:
                pass

            # Audible cue on Windows to signal dialog is open
            try:
                import platform
                if platform.system() == 'Windows':
                    import winsound
                    winsound.MessageBeep(winsound.MB_ICONASTERISK)
            except Exception:
                pass

            log_to_file("[Auth] Login window forced to front")
        except Exception as e:
            log_to_file(f"[Auth] Error forcing window visibility: {e}")
        
        # Now set as transient and grab input
        try:
            if (not is_standalone) and (not parent_was_hidden):
                win.transient(parent_root)
            win.grab_set()
            log_to_file("[Auth] Modal grab set")
        except Exception as e:
            log_to_file(f"[Auth] Error setting modal: {e}")

        # Block until closed
        log_to_file("[Auth] Waiting for login dialog to close")
        win.wait_window()  # Wait on the dialog itself, not the parent
        log_to_file(f"[Auth] Login dialog closed, result: {result.get('ok')}")
        
        # Hide parent again if it was hidden before (only for Toplevel case)
        if (not is_standalone) and parent_was_hidden:
            try:
                parent_root.withdraw()
                log_to_file("[Auth] Parent re-hidden after dialog")
            except Exception as e:
                log_to_file(f"[Auth] Error re-hiding parent: {e}")
        
        return bool(result.get("ok"))
    except Exception as e:
        log_to_file(f"[Auth] Login dialog error: {e}")
        log_exception("Login dialog (pre-HUD)")
        return False

def ensure_session_before_hud(parent_root) -> bool:
    """Ensure a valid session exists before showing HUD. Returns True if session is valid."""
    try:
        if _session_valid():
            log_to_file("[Auth] Session valid before HUD; proceeding")
            return True
        log_to_file("[Auth] No session; prompting before HUD")
        ok = show_login_dialog(parent_root)
        if ok:
            log_to_file("[Auth] Login success before HUD")
            return True
        log_to_file("[Auth] Login canceled before HUD")
        return False
    except Exception as e:
        log_to_file(f"[Auth] ensure_session_before_hud error: {e}")
        log_exception("ensure_session_before_hud")
        return False

# ----------------------------
# CONFIG (env-overridable)
# ----------------------------
CFG = {
    # Database config - using LOCAL MySQL for better performance
    "MYSQL_HOST": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "MYSQL_PORT": int(os.getenv("MYSQL_PORT", "3306")),
    "MYSQL_USER": os.getenv("MYSQL_USER", "local_uzr"),
    "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD", "fuck"),
    "MYSQL_DB": os.getenv("MYSQL_DB", "offta"),
    "MYSQL_LOCK_TIMEOUT": int(os.getenv("MYSQL_LOCK_TIMEOUT", "120")),
    
    # POLLING TABLE — QUEUE_WEBSITES ONLY
    "TABLE_NAME": os.getenv("TABLE_NAME", "queue_websites"),

    # Poll cadence & batch size
    "POLL_INTERVAL_SEC": float(os.getenv("POLL_INTERVAL_SEC", "1.0")),
    "CLAIM_BATCH_SIZE": int(os.getenv("CLAIM_BATCH_SIZE", "5")),

    # Reclaim stale 'running' rows (minutes). Set 0 to disable.
    "RECLAIM_MINUTES": int(os.getenv("RECLAIM_MINUTES", "2")),

    # Require both fields present
    "REQUIRE_BOTH_FIELDS": os.getenv("REQUIRE_BOTH_FIELDS", "1") in ("1", "true", "True"),

    # HTTP
    "HTTP_TIMEOUT": float(os.getenv("HTTP_TIMEOUT", "20")),
    "HTTP_UA": os.getenv(
        "HTTP_UA",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    
    # PHP Server Base URL (load from php_config.env or use default)
    "PHP_BASE_URL": PHP_BASE_URL,
    
    # Open PHP progress page in browser when triggering HTML processing
    "OPEN_PHP_PROGRESS_PAGE": os.getenv("OPEN_PHP_PROGRESS_PAGE", "1") in ("1", "true", "True"),
    
    # SMTP Email Configuration
    "SMTP_HOST": os.getenv("SMTP_HOST", "smtp.gmail.com"),
    "SMTP_PORT": int(os.getenv("SMTP_PORT", "587")),
    "SMTP_USER": os.getenv("SMTP_USER", ""),  # Your email address
    "SMTP_PASS": os.getenv("SMTP_PASS", ""),  # Your email password or app password
    "SMTP_FROM_EMAIL": os.getenv("SMTP_FROM_EMAIL", "noreply@offta.com"),
    "SMTP_FROM_NAME": os.getenv("SMTP_FROM_NAME", "Apartment Tracker"),
}

# ----------------------------
# Paths & runtime config
# ----------------------------
# Default BASE_DIR now points to <this_package_dir>/Captures so it matches your new layout.
# Still overridable via BASE_DIR env var.
PKG_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(os.getenv("BASE_DIR", str(PKG_DIR / "Captures")))
LOG_PATH = Path(os.getenv("LOG_PATH", str(BASE_DIR / "run.log")))
GLOBAL_JSON_PATH = BASE_DIR / "apartment_listings.json"
IMAGES_DIR = BASE_DIR / "images"

def today_dir() -> Path:
    return BASE_DIR / datetime.now().strftime("%Y-%m-%d")

# ----------------------------
# REMOTE TARGETS (env-overridable)
# ----------------------------
REMOTE_JSON_DIR = os.getenv(
    "REMOTE_JSON_DIR",
    "/home/daniel/api/trustyhousing.com/manual_upload/json_uploads"
)  # final file: apartment_listings.json

# Images parent: final will be /home/daniel/trustyhousing.com/app/public/images/...
REMOTE_IMAGES_PARENT = os.getenv(
    "REMOTE_IMAGES_PARENT",
    "/home/daniel/trustyhousing.com/app/public"
)

IMPORTER_URL = os.getenv("IMPORTER_URL", "https://172.104.206.182/xxxxx.php")
IMPORTER_VERIFY_TLS = os.getenv("IMPORTER_VERIFY_TLS", "0") in ("1", "true", "True")

# ----------------------------
# Telegram Settings
# ----------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "6893046625:AAEFvJKHA6x8agOMBPVKgXJdCYL4hr6vsKg")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "6702062204")
TELEGRAM_ENABLED   = os.getenv("TELEGRAM_ENABLED", "1") in ("1", "true", "True")

ERROR_NOTIFY_COOLDOWN_SEC = int(os.getenv("ERROR_NOTIFY_COOLDOWN_SEC", "60"))
_last_error_notif_ts = 0

# ----------------------------
# HUD — always required (fail fast if unavailable)
# ----------------------------
HUD_ENABLED = True  # force ON
HUD_OPACITY = float(os.getenv("HUD_OPACITY", "0.92"))

try:
    import tkinter as tk
    import tkinter.ttk as ttk
except Exception as e:
    # Hard fail: you said HUD must always be enabled
    print("FATAL: Tkinter is required for the HUD but is not available.\n", e, file=sys.stderr)
    sys.exit(2)

