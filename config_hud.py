#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OldCompactHUD class - main UI
Extracted from config_utils.py (lines 568-6588)

FILE STRUCTURE:
===============
Lines 1-42:     Database operations (update_db_status)
Lines 44-121:   Class initialization and public API
Lines 122-582:  UI Building (_build_ui method)
Lines 583-4555: Table management (Networks, Websites, Accounts tabs)
Lines 4557-5488: Job and step execution methods
Lines 5489-6350: Step implementation (_step_* methods)
Lines 6351-6427: Utility methods and mainloop
"""

from config_core import *
from config_hud_db import update_db_status
from config_helpers import launch_manual_browser, launch_manual_browser_docked_right, launch_manual_browser_docked_left
import threading
import re
from tkinter import messagebox

# Global dictionary to store address match completion callbacks
ADDRESS_MATCH_CALLBACKS = {}

# Global HUD instance (initialized by hud_start())
_hud: Optional['OldCompactHUD'] = None

class OldCompactHUD:
    """
    HUD runs its Tk mainloop on the MAIN THREAD.
    Worker threads post updates via a thread-safe Queue.
    """
    def __init__(self, opacity: float = 0.92):
        self._opacity = opacity
        self._inbox: "queue.Queue[tuple[str,str]]" = queue.Queue()
        self._paused = False
        self._collapsed = False

        # Counters
        self._q_count = 0
        self._r_count = 0
        self._d_count = 0
        self._e_count = 0

        # Build UI on main thread
        self._build_ui()

    # ---------- public API (thread-safe via queue) ----------
        self._cell_tooltips = {}  # Store error tooltips

    def push(self, text: str, level: str = "muted"):
        try:
            self._inbox.put_nowait(("MSG", f"{level}|{text}"))
        except Exception:
            pass

    def set_counts(self, queued: int, running: int, done: int, error: int):
        self._q_count = int(queued or 0)
        self._r_count = int(running or 0)
        self._d_count = int(done or 0)
        self._e_count = int(error or 0)
        try:
            self._inbox.put_nowait(("COUNTS", ""))
        except Exception:
            pass

    def set_paused(self, paused: bool):
        self._paused = bool(paused)
        try:
            self._inbox.put_nowait(("PAUSE", ""))
        except Exception:
            pass

    def is_paused(self) -> bool:
        return self._paused
    
    def _clear_ai_text(self):
        """Clear the AI text area"""
        if hasattr(self, '_ai_text'):
            self._ai_text.config(state="normal")
            self._ai_text.delete("1.0", "end")
            self._ai_text.config(state="disabled")
    
    def _append_ai_text(self, text: str, level: str = "muted"):
        """Append text to AI text area with color coding"""
        if not hasattr(self, '_ai_text'):
            return
        
        color_map = {
            "ok": "#2ECC71",
            "err": "#E74C3C",
            "warn": "#F4D03F",
            "info": "#58A6FF",
            "muted": "#A0A6AD"
        }
        
        color = color_map.get(level, "#E8EAED")
        
        self._ai_text.config(state="normal")
        self._ai_text.insert("end", text, level)
        self._ai_text.tag_config(level, foreground=color)
        self._ai_text.see("end")  # Auto-scroll to bottom
        self._ai_text.config(state="disabled")

    # ---------- UI ----------
    def _build_ui(self):
        root = tk.Tk()
        self._root = root
        
        # Add global exception handler for Tkinter
        def handle_exception(exc_type, exc_value, exc_traceback):
            msg = f"\n{'='*60}\nUNHANDLED EXCEPTION IN TKINTER:\n{'='*60}\n"
            print(msg)
            log_to_file(msg)
            tb.print_exception(exc_type, exc_value, exc_traceback)
            log_to_file(f"Exception: {exc_type.__name__}: {exc_value}")
            log_exception("TKINTER UNHANDLED EXCEPTION")
            print(f"{'='*60}\n")
            log_to_file(f"{'='*60}\n")
        
        root.report_callback_exception = lambda *args: handle_exception(*args)
        
        # Window close handler - clear session on exit
        def _on_close():
            try:
                _clear_session()
                log_to_file("[Auth] Session cleared on HUD close")
            except Exception:
                pass
            try:
                root.destroy()
            except Exception:
                pass
        
        root.protocol("WM_DELETE_WINDOW", _on_close)
        
        # Don't use overrideredirect to allow minimizing
        root.title("Queue Poller")
        try: 
            # Allow other windows to be on top - don't set -topmost
            root.wm_attributes("-alpha", self._opacity)
            # Make it look borderless but still minimizable
            if os.name == 'nt':  # Windows
                root.attributes('-toolwindow', True)
            root.resizable(False, False)
        except Exception: pass

        bg = "#101214"; fg = "#E8EAED"; muted = "#A0A6AD"; ok = "#2ECC71"; warn = "#F4D03F"; err = "#E74C3C"
        chip_bg = "#1A1D20"; chip_border = "#2A2F35"; accent = "#58A6FF"

        frame = tk.Frame(root, bg=bg, bd=0, highlightthickness=1, highlightbackground="#2A2F35")
        frame.pack(fill="both", expand=True)

        header = tk.Frame(frame, bg=bg)
        header.pack(fill="x", padx=8, pady=(6, 0))
        dot = tk.Canvas(header, width=10, height=10, highlightthickness=0, bg=bg, bd=0)
        dot.pack(side="left")
        self._dot = dot
        self._dot_id = dot.create_oval(2, 2, 8, 8, fill=ok, outline=ok)

        title = tk.Label(header, text="Queue Poller", font=("Segoe UI", 10, "bold"), fg=fg, bg=bg)
        title.pack(side="left", padx=(6, 0))
        spacer = tk.Frame(header, bg=bg); spacer.pack(side="left", expand=True, fill="x")

        # Window control buttons
        controls = tk.Frame(header, bg=bg)
        controls.pack(side="right", padx=(6, 0))
        
        # Close button
        close_btn = tk.Label(controls, text="✕", fg=muted, bg=bg, font=("Segoe UI", 10), padx=4, cursor="hand2")
        close_btn.pack(side="right", padx=(4, 0))
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=err))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=muted))
        close_btn.bind("<Button-1>", lambda e: _on_close())
        
        # Minimize button
        min_btn = tk.Label(controls, text="−", fg=muted, bg=bg, font=("Segoe UI", 10), padx=4, cursor="hand2")
        min_btn.pack(side="right", padx=(4, 0))
        min_btn.bind("<Enter>", lambda e: min_btn.config(fg=accent))
        min_btn.bind("<Leave>", lambda e: min_btn.config(fg=muted))
        min_btn.bind("<Button-1>", lambda e: root.iconify())

        # VPN Button and Location
        vpn_location_var = tk.StringVar(value="Not connected")
        def connect_vpn():
            import subprocess
            try:
                subprocess.run(["nordvpn", "connect"], check=True, shell=True)
                result = subprocess.run(["nordvpn", "status"], capture_output=True, text=True, shell=True)
                location = "Unknown"
                for line in result.stdout.splitlines():
                    if "Country:" in line:
                        location = line.split(":", 1)[1].strip()
                        break
                vpn_location_var.set(location)
            except Exception as e:
                vpn_location_var.set("Error")
                log_to_file(f"[VPN] Connection error: {e}")
        
        vpn_frame = tk.Frame(header, bg=bg)
        vpn_frame.pack(side="right", padx=(6, 0))
        vpn_btn = tk.Label(vpn_frame, text="VPN", fg="#FFFFFF", bg="#34495E", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
        vpn_btn.pack(side="left")
        vpn_btn.bind("<Button-1>", lambda e: threading.Thread(target=connect_vpn, daemon=True).start())
        vpn_btn.bind("<Enter>", lambda e: vpn_btn.config(bg="#4A6278"))
        vpn_btn.bind("<Leave>", lambda e: vpn_btn.config(bg="#34495E"))
        vpn_loc_lbl = tk.Label(vpn_frame, textvariable=vpn_location_var, fg=fg, bg=bg, font=("Segoe UI", 9))
        vpn_loc_lbl.pack(side="left", padx=(8, 0))
        # Connect to VPN on startup
        root.after(500, lambda: threading.Thread(target=connect_vpn, daemon=True).start())

        # Logout button (replaces Pause)
        self._btn = tk.Label(header, text="Logout", fg="#FFFFFF", bg="#E74C3C", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
        self._btn.pack(side="right", padx=(6, 0))

        # Logs toggle button
        logs_btn = tk.Label(header, text="Logs", fg=bg, bg=accent, font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
        logs_btn.pack(side="right", padx=(6, 0))
        logs_btn.bind("<Enter>", lambda e: logs_btn.config(bg="#6CB8FF"))
        logs_btn.bind("<Leave>", lambda e: logs_btn.config(bg=accent))

        # Right-aligned actions container so buttons are always visible from startup
        actions = tk.Frame(header, bg=bg)
        actions.pack(side="right", padx=(6, 0))

        # Accounts button
        accounts_btn = tk.Label(actions, text="Accounts", fg=bg, bg="#E67E22", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
        accounts_btn.pack(side="left", padx=(6, 0))
        accounts_btn.bind("<Enter>", lambda e: accounts_btn.config(bg="#F39C42"))
        accounts_btn.bind("<Leave>", lambda e: accounts_btn.config(bg="#E67E22"))

        # Mailer button
        mailer_btn = tk.Label(actions, text="Mailer", fg=bg, bg="#3498DB", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
        mailer_btn.pack(side="left", padx=(6, 0))
        mailer_btn.bind("<Enter>", lambda e: mailer_btn.config(bg="#5DADE2"))
        mailer_btn.bind("<Leave>", lambda e: mailer_btn.config(bg="#3498DB"))

        # Notifications button
        notifications_btn = tk.Label(actions, text="Notifications", fg=bg, bg="#E74C3C", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
        notifications_btn.pack(side="left", padx=(6, 0))
        notifications_btn.bind("<Enter>", lambda e: notifications_btn.config(bg="#F06C5C"))
        notifications_btn.bind("<Leave>", lambda e: notifications_btn.config(bg="#E74C3C"))

        # Extractor button (renamed from Queue) opens a table view of queued jobs
        extractor_btn = tk.Label(actions, text="Extractor", fg=bg, bg="#9B59B6", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
        extractor_btn.pack(side="left", padx=(6, 0))
        extractor_btn.bind("<Enter>", lambda e: extractor_btn.config(bg="#BB79D6"))
        extractor_btn.bind("<Leave>", lambda e: extractor_btn.config(bg="#9B59B6"))

        # Sync DB button - uploads tables to remote server
        sync_btn = tk.Label(actions, text="🔄 Sync DB", fg=bg, bg="#16A085", font=("Segoe UI", 9, "bold"), padx=8, pady=2, cursor="hand2")
        sync_btn.pack(side="left", padx=(6, 0))
        sync_btn.bind("<Enter>", lambda e: sync_btn.config(bg="#1ABC9C"))
        sync_btn.bind("<Leave>", lambda e: sync_btn.config(bg="#16A085"))

        # Ensure the window is wide enough to fit Accounts, Notifications, Extractor, Sync DB, Logs, Pause, and controls
        try:
            root.update_idletasks()
            # Compute required width based on header content
            required_w = max(header.winfo_reqwidth() + 20, actions.winfo_reqwidth() + 200, 1000)
            # Use requested height if actual height is not yet realized
            cur_h = root.winfo_height()
            if cur_h <= 1:
                cur_h = root.winfo_reqheight() or 400
            # Apply geometry and minsize so window stays wide enough
            root.geometry(f"{required_w}x{cur_h}")
            root.minsize(required_w, cur_h)
        except Exception as _e:
            try:
                root.geometry("1000x500")
                root.minsize(1000, 500)
            except Exception:
                pass

        # Live Log text area (initially hidden)
        ai_frame = tk.Frame(frame, bg=chip_bg, bd=1, relief="solid", highlightthickness=1, highlightbackground=chip_border)
        ai_label = tk.Label(ai_frame, text="📜 Live Log", font=("Segoe UI", 9, "bold"), fg=accent, bg=chip_bg, anchor="w")
        ai_label.pack(fill="x", padx=6, pady=(4, 2))
        
        # Scrolled text widget
        import tkinter.scrolledtext as scrolledtext
        ai_text = scrolledtext.ScrolledText(
            ai_frame, 
            height=10, 
            width=60,
            bg="#1A1D20",
            fg="#E8EAED",
            font=("Consolas", 8),
            insertbackground=accent,
            wrap="word",
            relief="flat",
            padx=4,
            pady=4
        )
        ai_text.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        ai_text.config(state="disabled")  # Read-only
        
        self._ai_frame = ai_frame
        self._ai_text = ai_text
        
        # Toggle logs visibility and resize window
        self._logs_visible = False
        def _toggle_logs(_e=None):
            """Open logs in a separate independent window"""
            try:
                # Create a new independent window for logs
                log_window = tk.Toplevel(root)
                log_window.title("Queue Poller - Full Debug Logs")
                log_window.geometry("900x600")
                
                # Don't make it transient - it should be independent
                # log_window.transient(root)  # Commented out to make it independent
                
                # Frame for the log viewer
                log_frame = tk.Frame(log_window, bg="#1A1D20")
                log_frame.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Title label
                title_label = tk.Label(
                    log_frame, 
                    text="Full Debug Logs (debug_queue.log)", 
                    fg="#E8EAED", 
                    bg="#1A1D20", 
                    font=("Segoe UI", 10, "bold")
                )
                title_label.pack(pady=(0, 5))
                
                # Scrolled text widget for logs
                import tkinter.scrolledtext as scrolledtext
                log_text = scrolledtext.ScrolledText(
                    log_frame,
                    bg="#1A1D20",
                    fg="#E8EAED",
                    font=("Consolas", 9),
                    insertbackground=accent,
                    wrap="word",
                    relief="flat",
                    padx=8,
                    pady=8
                )
                log_text.pack(fill="both", expand=True)
                
                # Read and display ALL logs from debug_queue.log
                log_file_path = Path(__file__).parent / "debug_queue.log"
                try:
                    if log_file_path.exists():
                        with open(log_file_path, 'r', encoding='utf-8') as f:
                            log_content = f.read()
                        log_text.insert("1.0", log_content)
                        log_text.see("end")  # Scroll to bottom
                        log_text.config(state="disabled")  # Make read-only
                    else:
                        log_text.insert("1.0", "No log file found at:\n" + str(log_file_path))
                        log_text.config(state="disabled")
                except Exception as read_err:
                    log_text.insert("1.0", f"Error reading log file:\n{read_err}")
                    log_text.config(state="disabled")
                
                # Button frame at bottom
                button_frame = tk.Frame(log_window, bg="#1A1D20")
                button_frame.pack(fill="x", padx=10, pady=(5, 10))
                
                # Refresh button
                def refresh_logs():
                    try:
                        log_text.config(state="normal")
                        log_text.delete("1.0", "end")
                        if log_file_path.exists():
                            with open(log_file_path, 'r', encoding='utf-8') as f:
                                log_content = f.read()
                            log_text.insert("1.0", log_content)
                            log_text.see("end")
                        log_text.config(state="disabled")
                    except Exception as e:
                        print(f"Error refreshing logs: {e}")
                
                refresh_btn = tk.Button(
                    button_frame,
                    text="🔄 Refresh",
                    command=refresh_logs,
                    bg="#2ECC71",
                    fg="#fff",
                    font=("Segoe UI", 9, "bold"),
                    padx=15,
                    pady=5,
                    relief="flat",
                    cursor="hand2"
                )
                refresh_btn.pack(side="left", padx=5)
                
                # Copy button
                def copy_logs():
                    try:
                        log_text.config(state="normal")
                        log_content = log_text.get("1.0", "end-1c")
                        log_text.config(state="disabled")
                        log_window.clipboard_clear()
                        log_window.clipboard_append(log_content)
                        log_window.update()
                        # Briefly change button text to show success
                        copy_btn.config(text="✓ Copied!")
                        log_window.after(1500, lambda: copy_btn.config(text="📋 Copy All"))
                    except Exception as e:
                        print(f"Error copying logs: {e}")
                
                copy_btn = tk.Button(
                    button_frame,
                    text="📋 Copy All",
                    command=copy_logs,
                    bg="#3498DB",
                    fg="#fff",
                    font=("Segoe UI", 9, "bold"),
                    padx=15,
                    pady=5,
                    relief="flat",
                    cursor="hand2"
                )
                copy_btn.pack(side="left", padx=5)
                
                # Clear logs button
                def clear_logs():
                    try:
                        with open(log_file_path, 'w', encoding='utf-8') as f:
                            f.write("")
                        log_text.config(state="normal")
                        log_text.delete("1.0", "end")
                        log_text.insert("1.0", "Logs cleared.")
                        log_text.config(state="disabled")
                    except Exception as e:
                        print(f"Error clearing logs: {e}")
                
                clear_btn = tk.Button(
                    button_frame,
                    text="🗑️ Clear Logs",
                    command=clear_logs,
                    bg="#E74C3C",
                    fg="#fff",
                    font=("Segoe UI", 9, "bold"),
                    padx=15,
                    pady=5,
                    relief="flat",
                    cursor="hand2"
                )
                clear_btn.pack(side="left", padx=5)
                
                # Close button
                close_btn = tk.Button(
                    button_frame,
                    text="✖ Close",
                    command=log_window.destroy,
                    bg="#95A5A6",
                    fg="#fff",
                    font=("Segoe UI", 9, "bold"),
                    padx=15,
                    pady=5,
                    relief="flat",
                    cursor="hand2"
                )
                close_btn.pack(side="right", padx=5)
                
            except Exception as ex:
                print(f"Error opening log window: {ex}")
                log_to_file(f"[Queue] Error opening log window: {ex}")
        
        logs_btn.bind("<Button-1>", _toggle_logs)
        
        hint = tk.Label(header, text="⤢", fg=muted, bg=bg, font=("Segoe UI Symbol", 11)); hint.pack(side="right", padx=(6, 0))

        body = tk.Frame(frame, bg=bg); body.pack(fill="both", expand=True, padx=8, pady=(6, 8))
        
        # Metro selector row (its own line, aligned to right)
        metro_row = tk.Frame(body, bg=bg)
        metro_row.pack(fill="x", pady=(0, 8))
        
        self._selected_metro = tk.StringVar(value="Seattle")
        metro_container = tk.Frame(metro_row, bg=bg)
        metro_container.pack(side="right", padx=(0, 0))
        
        self._metro_lbl = tk.Label(metro_container, text="Metro:", fg=bg, bg="#2ECC71", font=("Segoe UI", 9, "bold"), padx=6, pady=1)
        self._metro_lbl.pack(side="left", padx=(0, 4))
        self._metro_combo = ttk.Combobox(metro_container, textvariable=self._selected_metro, width=18, state="readonly", values=["Seattle"])
        self._metro_combo.pack(side="left", padx=(0, 0))
        self._metro_combo.current(0)  # Set to Seattle by default
        # Small loader next to metro combobox (hidden by default)
        try:
            self._metro_pb = ttk.Progressbar(metro_container, mode="indeterminate", length=64)
            self._metro_pb.pack(side="left", padx=(6, 0))
            # Hide initially
            self._metro_pb.stop()
            self._metro_pb.pack_forget()
        except Exception:
            self._metro_pb = None
        
        # Loader area (hidden by default)
        loader = tk.Frame(body, bg=bg)
        loader.pack(fill="x")
        self._loader = loader
        # Progress bar (indeterminate)
        try:
            self._pb = ttk.Progressbar(loader, mode="indeterminate", length=180)
            self._pb.pack(side="left", padx=(0,8))
        except Exception:
            self._pb = None
        self._loader_label = tk.Label(loader, text="", fg=muted, bg=bg, font=("Segoe UI", 9))
        self._loader_label.pack(side="left", expand=True, fill="x")
        # Hidden initially
        loader.pack_forget()
        
        # Stats chips removed - not showing data

        root.update_idletasks()
        sw = root.winfo_screenwidth()
        x_pos = int(sw * 0.20)  # 20% from left edge
        root.geometry(f"360x120+{x_pos}+0")  # Position at top of screen

        # Drag
        def start_move(e):
            root._x, root._y = e.x, e.y
        def do_move(e):
            try:
                root.geometry(f"+{root.winfo_x() + (e.x - root._x)}+{root.winfo_y() + (e.y - root._y)}")
            except Exception:
                pass
        header.bind("<Button-1>", start_move)
        header.bind("<B1-Motion>", do_move)

        # Logout handler (hide HUD, clear session, re-prompt or quit)
        def _on_logout(_e=None):
            try:
                _clear_session()
                log_to_file("[Auth] Logout clicked - clearing session")
                
                # Hide HUD immediately
                try:
                    root.withdraw()
                    root.update()  # Force update
                except Exception as e:
                    log_to_file(f"[Auth] Error hiding HUD: {e}")
                
                # Force process pending events before showing login
                try:
                    root.update_idletasks()
                except Exception:
                    pass
                
                # Re-prompt with HUD hidden
                log_to_file("[Auth] Showing login dialog after logout")
                ok_login = show_login_dialog(root)
                log_to_file(f"[Auth] Login result: {ok_login}")
                
                if ok_login:
                    # Restore HUD and update status
                    log_to_file("[Auth] Restoring HUD after successful login")
                    try:
                        root.deiconify()
                        root.lift()
                        root.focus_force()
                        root.update()
                    except Exception as e:
                        log_to_file(f"[Auth] Error showing HUD: {e}")
                    self._set_last_line("Signed in.", "ok")
                else:
                    # User canceled login; quit app
                    log_to_file("[Auth] Login canceled - quitting app")
                    try:
                        root.destroy()
                    except Exception:
                        pass
            except Exception as e:
                log_to_file(f"[Auth] Logout error: {e}")
                log_exception("Logout handler")

        # Bind logout
        self._btn.bind("<Button-1>", _on_logout)

        # Poll inbox
        def _poll():
            try:
                while True:
                    tag, payload = self._inbox.get_nowait()
                    if tag == "MSG":
                        level, text = payload.split("|", 1)
                        self._set_last_line(text, level)
                    elif tag == "COUNTS":
                        self._apply_counts()
                    elif tag == "PAUSE":
                        # Pause state changed; no UI change as Pause was replaced by Logout
                        pass
                    elif tag == "LOADER_SHOW":
                        self._show_loader(payload or "")
                    elif tag == "LOADER_MSG":
                        self._set_loader_msg(payload or "")
                    elif tag == "LOADER_HIDE":
                        self._hide_loader()
            except queue.Empty:
                pass
            root.after(120, _poll)

        root.after(120, _poll)

        # ---------- Queue Table (embedded below chips) ----------
        # Create tabbed notebook for different queue tables
        self._queue_frame = tk.Frame(body, bg=chip_bg, bd=1, relief="solid", highlightthickness=1, highlightbackground=chip_border)
        self._queue_visible = False
        
        # Tab controls header (MOVED ABOVE status chips position)
        tab_header = tk.Frame(self._queue_frame, bg=chip_bg)
        tab_header.pack(fill="x", padx=4, pady=4)
        
        # Date dropdown (populated from network_daily_stats)
        date_frame = tk.Frame(tab_header, bg=chip_bg)
        date_frame.pack(side="left", padx=(4, 12))
        
        date_label = tk.Label(date_frame, text="Date:", fg=muted, bg=chip_bg, font=("Segoe UI", 9, "bold"))
        date_label.pack(side="left", padx=(0, 4))
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        self._selected_date = tk.StringVar(value=today_str)
        self._date_combo = ttk.Combobox(date_frame, textvariable=self._selected_date, width=12, state="readonly", values=[today_str])
        self._date_combo.pack(side="left")
        self._date_combo.current(0)
        
        # Load dates from database in background
        def _load_dates():
            try:
                import mysql.connector
                conn = mysql.connector.connect(
                    host='localhost',
                    port=3306,
                    user='root',
                    password='',
                    database='offta',
                    connect_timeout=10
                )
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT date FROM network_daily_stats ORDER BY date DESC LIMIT 30")
                dates = [str(row[0]) for row in cursor.fetchall()]
                cursor.close()
                conn.close()
                
                # Always ensure today's date is in the list (even if no data exists yet)
                if today_str not in dates:
                    dates.insert(0, today_str)  # Add today at the beginning
                
                def _update_dates():
                    # Preserve current selection
                    current_selection = self._selected_date.get()
                    self._date_combo.config(values=dates)
                    # Restore selection if it's still in the list, otherwise default to today
                    if current_selection in dates:
                        self._date_combo.set(current_selection)
                    else:
                        # Default to today
                        self._date_combo.set(today_str)
                
                self._root.after(0, _update_dates)
                log_to_file(f"[Queue] Loaded {len(dates)} dates from network_daily_stats (today always included)")
            except Exception as e:
                log_to_file(f"[Queue] Failed to load dates: {e}")
        
        threading.Thread(target=_load_dates, daemon=True).start()
        
        # Bind date change to refresh table
        self._date_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_queue_table())
        
        tab_label = tk.Label(tab_header, text="Table:", fg=muted, bg=chip_bg, font=("Segoe UI", 9))
        tab_label.pack(side="left", padx=(0, 6))
        
        tab_btns_frame = tk.Frame(tab_header, bg=chip_bg)
        tab_btns_frame.pack(side="left")

        # Accounts tab search UI (shown only when Accounts tab is active)
        accounts_search_frame = tk.Frame(tab_header, bg=chip_bg)
        self._accounts_search_var = tk.StringVar(value="")
        accounts_search_label = tk.Label(accounts_search_frame, text="Search:", fg=muted, bg=chip_bg, font=("Segoe UI", 9))
        accounts_search_entry = tk.Entry(accounts_search_frame, textvariable=self._accounts_search_var, width=18)
        accounts_search_button = tk.Button(accounts_search_frame, text="Go", bg=accent, fg=bg, padx=6, pady=1,
                                           font=("Segoe UI", 8, "bold"), relief="flat",
                                           command=lambda: self._refresh_queue_table())
        accounts_search_label.pack(side="left")
        accounts_search_entry.pack(side="left", padx=(4, 4))
        accounts_search_button.pack(side="left")
        
        self._current_status = tk.StringVar(value="all")
        self._current_table = tk.StringVar(value="queue_websites")
        # Independent status per table
        self._tab_status = {
            "listing_networks": "all",
            "queue_websites": "all",
            "listing_websites": "all",
            "websites": "all",
            "parcel": "all",
            "code": "all",
            "911": "all",
            "accounts": "all",
        }
        
        # Store tab button references and counts
        self._tab_buttons = {}
        self._tab_counts = {}
        
        def make_tab_btn(text, table_name):
            btn = tk.Label(tab_btns_frame, text=text, fg=muted, bg=chip_border, font=("Segoe UI", 8, "bold"), padx=6, pady=1, cursor="hand2")
            btn.pack(side="left", padx=1)
            def on_click(_e):
                try:
                    log_to_file(f"[Queue] ========== TAB CLICKED: {text} (table_name={table_name}) ==========")
                    # Show loading indicator for Networks, Parcel, Code, 911 tabs
                    if table_name.lower() in ('listing_networks', 'networks', 'parcel', 'code', '911'):
                        try:
                            if hasattr(self, '_show_loading'):
                                self._show_loading()
                        except Exception as load_err:
                            log_to_file(f"[Queue] Could not show loading: {load_err}")
                    
                    log_to_file(f"[Queue] Setting _current_table to: {table_name}")
                    self._current_table.set(table_name)
                    # Restore per-table status selection
                    try:
                        saved_status = self._tab_status.get(table_name, "all")
                        log_to_file(f"[Queue] Restoring status filter for {table_name}: {saved_status}")
                        self._current_status.set(saved_status)
                    except Exception:
                        pass
                    # Show/hide tab-specific controls
                    try:
                        if table_name == 'accounts':
                            accounts_search_frame.pack(side="left", padx=(12, 0))
                        else:
                            accounts_search_frame.pack_forget()
                        
                        # Show Parcel refresh button only when Parcel tab is active
                        if hasattr(self, '_parcel_refresh_frame'):
                            if table_name.lower() == 'parcel':
                                self._parcel_refresh_frame.pack(side="left", padx=(12, 0))
                            else:
                                self._parcel_refresh_frame.pack_forget()
                    except Exception:
                        pass
                    # Metro dropdown is now always visible in the top header; no show/hide per tab
                    log_to_file(f"[Queue] About to call _refresh_queue_table() for table: {table_name}")
                    self._refresh_queue_table()
                    log_to_file(f"[Queue] _refresh_queue_table() completed for table: {table_name}")
                    # Refresh counts for new table
                    if hasattr(self, '_refresh_status_counts'):
                        try:
                            self._refresh_status_counts()
                        except Exception as _cnt_err:
                            log_to_file(f"[Queue] Count refresh error (ignored): {_cnt_err}")
                    # Update all tab buttons
                    for child in tab_btns_frame.winfo_children():
                        try:
                            child.config(bg=chip_border, fg=muted)
                        except Exception:
                            pass
                    try:
                        btn.config(bg=accent, fg=bg)
                    except Exception:
                        pass
                    # Always hide Accounts search UI when clicking regular tabs
                    try:
                        accounts_search_frame.pack_forget()
                    except Exception:
                        pass
                except Exception as _tab_err:
                    log_to_file(f"[Queue] Tab click error: {_tab_err}")
                    log_exception("Tab click handler")
                    try:
                        self._queue_status_label.config(text=f"Error loading tab: {_tab_err}")
                    except Exception:
                        pass
            btn.bind("<Button-1>", on_click)
            self._tab_buttons[table_name] = btn
            return btn
        
        # Order determines left-to-right placement; put Networks first (leftmost)
        tab_networks = make_tab_btn("Networks", "queue_websites")
        tab_websites = make_tab_btn("Websites", "listing_websites")
        tab_parcel = make_tab_btn("Parcel", "parcel")
        tab_code = make_tab_btn("Code", "code")
        tab_911 = make_tab_btn("911", "911")
        
        # Set initial active tab
        tab_networks.config(bg=accent, fg=bg)
        
        # Status filter section (AFTER table tabs)
        status_label = tk.Label(tab_header, text="Status:", fg=muted, bg=chip_bg, font=("Segoe UI", 9))
        status_label.pack(side="left", padx=(12, 6))
        
        # Status filter buttons
        status_frame = tk.Frame(tab_header, bg=chip_bg)
        status_frame.pack(side="left")
        
        # Store status button references
        self._status_buttons = {}
        self._status_counts = {"all": 0, "queued": 0, "running": 0, "done": 0, "error": 0}
        
        def make_status_btn(text, status_val, color):
            btn = tk.Label(status_frame, text=f"{text} (0)", fg=bg, bg=color, font=("Segoe UI", 8, "bold"), padx=6, pady=1, cursor="hand2")
            btn.pack(side="left", padx=2)
            def on_click(_e):
                self._current_status.set(status_val)
                try:
                    tbl = self._current_table.get()
                    self._tab_status[tbl] = status_val
                except Exception:
                    pass
                self._refresh_queue_table()
            btn.bind("<Button-1>", on_click)
            self._status_buttons[status_val] = btn
            return btn
        
        make_status_btn("All", "all", muted)
        make_status_btn("Queued", "queued", accent)
        make_status_btn("Running", "running", warn)
        make_status_btn("Done", "done", ok)
        make_status_btn("Error", "error", err)
        
        # Refresh button for Parcel tab (hidden by default, shown only when Parcel is active)
        parcel_refresh_frame = tk.Frame(tab_header, bg=chip_bg)
        parcel_refresh_btn = tk.Button(
            parcel_refresh_frame,
            text="🔄 Refresh",
            bg="#3498DB",
            fg="#fff",
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=1,
            relief="flat",
            cursor="hand2",
            command=lambda: self._trigger_parcel_refresh() if hasattr(self, '_trigger_parcel_refresh') else None
        )
        parcel_refresh_btn.pack(side="left")
        
        # Hover effects for parcel refresh button
        def on_enter_parcel_refresh(e):
            parcel_refresh_btn.config(bg="#2980B9")
        def on_leave_parcel_refresh(e):
            parcel_refresh_btn.config(bg="#3498DB")
        parcel_refresh_btn.bind("<Enter>", on_enter_parcel_refresh)
        parcel_refresh_btn.bind("<Leave>", on_leave_parcel_refresh)
        
        # Hide by default
        self._parcel_refresh_frame = parcel_refresh_frame
        
        # Treeview table
        tree_frame = tk.Frame(self._queue_frame, bg=chip_bg)
        tree_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
        
        cols = ("ID", "Link", "Metro", "Int", "Last", "Next", "Status", "Δ$", "+", "-", "Total", "✏️", "hidden1", "hidden2")
        self._queue_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)

        # Configure row tag colors for zebra striping and status-based coloring
        try:
            self._queue_tree.tag_configure("even", background="#FFFFFF")           # white
            self._queue_tree.tag_configure("odd", background="#E6F7FF")            # light blue
            self._queue_tree.tag_configure("done_row", background="#D4EDDA")       # light green
            self._queue_tree.tag_configure("error_row", background="#F8D7DA")      # light red
            self._queue_tree.tag_configure("running_row", background="#FFF3CD")    # light yellow
        except Exception as tag_err:
            log_to_file(f"[Queue] Tag config error: {tag_err}")

        # Default column setup
        def _apply_columns(labels, widths):
            try:
                for c, label in zip(cols, labels):
                    self._queue_tree.heading(c, text=label)
                for c, w in zip(cols, widths):
                    # If width is 0, hide the column fully (no stretch, minwidth=0)
                    if w <= 0:
                        try:
                            self._queue_tree.column(c, width=0, minwidth=0, stretch=False, anchor="center")
                        except Exception:
                            self._queue_tree.column(c, width=0, anchor="center")
                    else:
                        self._queue_tree.column(c, width=w, anchor="center")
            except Exception as _colerr:
                log_to_file(f"[Queue] Column setup error: {_colerr}")

        DEFAULT_LABELS = ["ID", "Link", "Metro", "Int", "Last", "Next", "Status", "Δ$", "+", "-", "Total", "✏️", "", ""]
        DEFAULT_WIDTHS = [40, 200, 80, 40, 70, 70, 50, 40, 35, 35, 50, 30, 0, 0]
        _apply_columns(DEFAULT_LABELS, DEFAULT_WIDTHS)

        # Helper to dynamically adjust columns per tab
        def _set_queue_columns_for_table(table_name: str, custom_source: str | None = None):
            t = (table_name or "").lower()
            log_to_file(f"[Queue] Column config: table_name={table_name}, custom_source={custom_source}, t={t}")
            labels = DEFAULT_LABELS[:]
            widths = DEFAULT_WIDTHS[:]
            try:
                if t in ("listing_websites", "websites") or custom_source == "websites":
                    labels[1] = "Website"
                    labels[3] = "Name"
                    widths[1] = 260
                    widths[3] = 180
                elif t == "parcel":
                    labels[1] = "Parcel Link"
                    labels[2] = "Total Addresses"
                    labels[3] = "Metro"
                    labels[4] = "Empty Parcels"
                    widths[1] = 260
                    widths[2] = 120
                    widths[3] = 140
                    widths[4] = 120
                elif t == "accounts" or custom_source == "accounts":
                    labels[1] = "Email"
                    labels[3] = "Name"
                    labels[4] = "Role • Seen"
                    widths[1] = 220
                    widths[3] = 180
                    widths[4] = 180
                elif t in ("queue_websites"):
                    # Networks table: Hide Metro column (width=0)
                    widths[2] = 0  # Hide Metro column for Networks
                    log_to_file(f"[Queue] Column config: Using Networks config (Metro hidden)")
                elif t in ("listing_websites", "websites"):
                    # Websites table: Change labels - Metro shows "Seattle", Int shows "Avail Website" (building name)
                    labels[2] = "Metro"           # Column 3: Metro (Seattle)
                    labels[3] = "Avail Website"   # Column 4: Avail Website (Building Name)
                    widths[2] = 100               # Metro width (smaller since it's just "Seattle")
                    widths[3] = 250               # Avail Website width (for building names)
                    log_to_file(f"[Queue] Column config: Using Websites config (Metro=Seattle, Avail Website=Building Name)")
                # otherwise default
            except Exception as _maperr:
                log_to_file(f"[Queue] Column mapping error: {_maperr}")
            log_to_file(f"[Queue] Column config: Final config has {len(labels)} columns")
            _apply_columns(labels, widths)
        self._set_queue_columns_for_table = _set_queue_columns_for_table

        # Local overrides and tooltips for per-cell messages (e.g., capture errors)
        self._local_step_overrides = {}

        # Event bindings for tooltips and click-to-copy
        def _on_tree_motion(event):
            """Show tooltip for error messages"""
            try:
                item = self._queue_tree.identify_row(event.y)
                column = self._queue_tree.identify_column(event.x)
                
                if item and column:
                    tooltip_key = f"{item}|{column}"
                    if tooltip_key in self._cell_tooltips:
                        # Show tooltip
                        _hide_tooltip()
                        msg = self._cell_tooltips[tooltip_key]
                        
                        # Create tooltip window
                        tip = tk.Toplevel()
                        tip.wm_overrideredirect(True)
                        x = event.x_root + 10
                        y = event.y_root + 10
                        tip.wm_geometry(f"+{x}+{y}")
                        
                        label = tk.Label(tip, text=msg, background="#ffffe0",
                                       relief="solid", borderwidth=1,
                                       font=("Segoe UI", 9))
                        label.pack()
                        self._active_tooltip = tip
                    else:
                        _hide_tooltip()
                else:
                    _hide_tooltip()
            except Exception:
                pass
        
        def _on_tree_click(event):
            """Copy error message to clipboard on click"""
            try:
                item = self._queue_tree.identify_row(event.y)
                column = self._queue_tree.identify_column(event.x)
                
                # Get column index (Status is usually column 5 or 6)
                if item and column:
                    tooltip_key = f"{item}|{column}"
                    if tooltip_key in self._cell_tooltips:
                        msg = self._cell_tooltips[tooltip_key]
                        self._root.clipboard_clear()
                        self._root.clipboard_append(msg)
                        print(f"Copied to clipboard: {msg[:50]}...")
            except Exception as e:
                print(f"Click error: {e}")
        
        self._queue_tree.bind("<Motion>", _on_tree_motion)
        self._queue_tree.bind("<Button-1>", _on_tree_click)
        self._queue_tree.bind("<Leave>", lambda e: _hide_tooltip())

        self._cell_tooltips = {}
        self._active_tooltip = None

        def _hide_tooltip():
            try:
                if self._active_tooltip is not None:
                    self._active_tooltip.destroy()
            except Exception:
                pass
            self._active_tooltip = None

        def _show_tooltip(text: str, x: int, y: int):
            _hide_tooltip()
            try:
                tip = tk.Toplevel(self._queue_tree)
                tip.wm_overrideredirect(True)
                tip.attributes('-topmost', True)
                # position near the cursor
                tip.geometry(f"+{x+16}+{y+16}")
                label = tk.Label(tip, text=text, bg="#222", fg="#fff", bd=1, relief="solid", padx=6, pady=3, font=("Segoe UI", 8))
                label.pack()
                self._active_tooltip = tip
            except Exception as _te:
                log_to_file(f"[Queue] Tooltip error: {_te}")

        def _on_tree_motion(event):
            try:
                row = self._queue_tree.identify_row(event.y)
                col = self._queue_tree.identify_column(event.x)
                if not row or not col:
                    _hide_tooltip()
                    return
                key = (row, col)
                if key in self._cell_tooltips:
                    # Convert to screen coords
                    x_root = self._queue_tree.winfo_rootx() + event.x
                    y_root = self._queue_tree.winfo_rooty() + event.y
                    _show_tooltip(self._cell_tooltips[key], x_root, y_root)
                else:
                    _hide_tooltip()
            except Exception as _me:
                log_to_file(f"[Queue] Motion handler error: {_me}")
                _hide_tooltip()

        self._queue_tree.bind('<Motion>', _on_tree_motion)
        self._queue_tree.bind('<Leave>', lambda _e: _hide_tooltip())

        # Prevent crashes from clicking on tree
        def safe_tree_click(event):
            try:
                log_to_file(f"[Queue] Tree clicked at x={event.x}, y={event.y}")
                
                # Get the clicked region
                region = self._queue_tree.identify_region(event.x, event.y)
                log_to_file(f"[Queue] Clicked region: {region}")
                
                if region != "cell":
                    log_to_file(f"[Queue] Not a cell, ignoring click")
                    return
                
                # Get the clicked item and column
                item = self._queue_tree.identify_row(event.y)
                column = self._queue_tree.identify_column(event.x)
                
                log_to_file(f"[Queue] Item: {item}, Column: {column}")
                
                if not item:
                    log_to_file(f"[Queue] No item found, ignoring click")
                    return
                
                # Map columns to steps (columns #6-#11 are the step columns now)
                step_map = {
                    "#6": "capture_html",      # 1.HTML
                    "#7": "create_json",        # 2.JSON
                    "#8": "manual_match",       # 3.Extract (download/extract images)
                    "#9": "process_db",         # 4.Upload (upload images to server)
                    "#10": "insert_db",          # 5.Insert DB
                    "#11": "address_match"       # 6.Address Match
                }
                
                # Handle ID column click (column #1) - open Activity Window
                if column == "#1":
                    # Get job details
                    values = self._queue_tree.item(item, "values")
                    if not values or len(values) == 0:
                        return
                    # Extract job_id from "▶ 123" format
                    job_id_str = str(values[0]).replace("▶", "").strip()
                    try:
                        job_id = int(job_id_str)
                    except:
                        job_id = job_id_str
                    table = self._current_table.get()
                    
                    # For Websites tab, check if Availability_Website exists
                    if str(table).lower() in ('listing_websites', 'websites'):
                        try:
                            import mysql.connector
                            conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                            cursor = conn.cursor()
                            cursor.execute("SELECT availability_website FROM google_places WHERE id = %s", (job_id,))
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()
                            
                            if not result or not result[0] or str(result[0]).strip() == '':
                                # No Availability_Website - show edit dialog instead
                                log_to_file(f"[Queue] Websites row {job_id} missing Availability_Website - opening edit dialog")
                                self._show_edit_dialog(job_id, table)
                                return
                        except Exception as check_err:
                            log_to_file(f"[Queue] Failed to check Availability_Website: {check_err}")
                            # Continue anyway if check fails
                    
                    # Get screen dimensions and calculate 20% width and 100% height
                    screen_width = self._root.winfo_screenwidth()
                    screen_height = self._root.winfo_screenheight()
                    window_width = int(screen_width * 0.20)  # 20% of screen width
                    window_height = int(screen_height * 0.96)  # 96% height (leave space at bottom)
                    
                    # Show progress/status window for steps - positioned at top-left
                    steps = [
                        "Step 1: Fetch HTML",
                        "Step 2: Create JSON",
                        "Step 3: Extract Data",
                        "Step 4: Upload",
                        "Step 5: Insert DB",
                        "Step 6: Address Match"
                    ]
                    status_win = tk.Toplevel(self._queue_tree)
                    # Simple window title: Job X - Activity Monitor
                    status_win.title(f"Job {job_id} - Activity Monitor")
                    status_win.geometry(f"{window_width}x{window_height}+0+0")  # 20% width, 96% height at top-left (0,0)
                    
                    # --- Per-job stats for Networks Summary column ---
                    job_stats = {
                        'listings': 0,
                        'images': 0,
                        'uploaded': 0,
                        'skipped': 0,
                        'failed': 0,
                        'new': 0,
                        'price_changes': 0,
                        'inactive': 0,
                        'api_calls': 0,
                        'total_time_sec': 0,
                    }

                    # Helper function to get network_id from queue_websites
                    def get_network_id():
                        """Get network_id from queue_websites.source_table"""
                        try:
                            import mysql.connector
                            conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                            cursor = conn.cursor()
                            cursor.execute("SELECT source_table FROM queue_websites WHERE id = %s", (job_id,))
                            result = cursor.fetchone()
                            cursor.close()
                            conn.close()
                            if result:
                                try:
                                    return int(result[0])
                                except:
                                    return None
                        except Exception as db_err:
                            log_to_file(f"[Queue] Failed to get network_id: {db_err}")
                        return None

                    def _fmt_total(sec):
                        try:
                            if sec is None:
                                return ""
                            sec = int(sec)
                            if sec < 60:
                                return f"{sec}s"
                            m = sec // 60
                            s = sec % 60
                            return f"{m}m {s}s"
                        except Exception:
                            return ""

                    def _build_summary_text():
                        parts = []
                        try:
                            if job_stats.get('listings', 0):
                                parts.append(f"Listings {job_stats['listings']}")
                            if job_stats.get('images', 0):
                                parts.append(f"Images {job_stats['images']}")
                            up = job_stats.get('uploaded', 0)
                            sk = job_stats.get('skipped', 0)
                            fl = job_stats.get('failed', 0)
                            if any([up, sk, fl]):
                                parts.append(f"Uploaded {up}/{sk}/{fl}")
                            if job_stats.get('new', 0):
                                parts.append(f"New {job_stats['new']}")
                            if job_stats.get('price_changes', 0):
                                parts.append(f"Δ {job_stats['price_changes']}")
                            if job_stats.get('inactive', 0):
                                parts.append(f"Inactive {job_stats['inactive']}")
                            if job_stats.get('api_calls', 0):
                                parts.append(f"API {job_stats['api_calls']}")
                            tt = _fmt_total(job_stats.get('total_time_sec'))
                            if tt:
                                parts.append(f"Total {tt}")
                        except Exception:
                            pass
                        return " | ".join(parts) if parts else "-"

                    def _update_summary_on_table():
                        try:
                            # Only render summary for Networks tab (steps hidden)
                            tbl_now = str(self._current_table.get() or '').lower()
                            if tbl_now not in ('queue_websites', 'listing_websites', 'websites'):
                                return
                            wanted = str(job_id)
                            for rid in self._queue_tree.get_children():
                                vals = list(self._queue_tree.item(rid, 'values') or [])
                                if not vals:
                                    continue
                                jid_raw = str(vals[0] or '')
                                jid_clean = jid_raw.replace('▶', '').strip()
                                if jid_clean == wanted:
                                    # Summary maps to column index 3 (0-based) for Networks mapping
                                    if len(vals) > 3:
                                        vals[3] = _build_summary_text()
                                        self._queue_tree.item(rid, values=tuple(vals))
                                    break
                        except Exception as _userr:
                            log_to_file(f"[Queue] Update summary failed: {_userr}")
                    
                    # Main container with PanedWindow for side-by-side layout
                    paned_window = tk.PanedWindow(status_win, orient=tk.HORIZONTAL, bg="#1e1e1e", sashwidth=5, sashrelief=tk.RAISED)
                    paned_window.pack(fill="both", expand=True)
                    
                    # Left pane - Activity Window
                    main_frame = tk.Frame(paned_window, bg="#1e1e1e")
                    paned_window.add(main_frame, width=window_width)
                    
                    # Right pane - JSON Stats (initially hidden, will be shown after Step 2)
                    json_stats_frame = tk.Frame(paned_window, bg="#1e1e1e", width=0)
                    json_stats_visible = [False]  # Track if stats panel is visible
                    
                    # Status indicators frame
                    status_frame = tk.Frame(main_frame, bg="#1e1e1e")
                    status_frame.pack(fill="x", padx=10, pady=10)
                    status_labels = []
                    status_path_labels = []  # For showing paths next to status
                    status_time_labels = []  # For showing time/duration next to status
                    status_summary_labels = []  # For showing step summaries (stats)
                    step_start_times = {}  # Track when each step started
                    workflow_start_time = [None]  # Track when the full workflow started
                    step_completed = [False, False, False, False, False, False]  # Track completion status
                    
                    # Store retry count in a way that persists across function calls
                    class RetryCounter:
                        def __init__(self):
                            self.count = 0
                    
                    step1_retry_counter = RetryCounter()
                    
                    for i, step in enumerate(steps):
                        step_container = tk.Frame(status_frame, bg="#1e1e1e")
                        step_container.pack(fill="x", pady=2)
                        
                        # Main status label
                        lbl = tk.Label(step_container, text=f"{step} - Pending", anchor="w", bg="#1e1e1e", fg="#888", font=("Consolas", 8))
                        lbl.pack(side="top", fill="x")
                        status_labels.append(lbl)
                        
                        # Path label (initially empty)
                        path_lbl = tk.Label(step_container, text="", anchor="w", bg="#1e1e1e", fg="#00aaff", font=("Consolas", 7), cursor="hand2")
                        path_lbl.pack(side="top", fill="x", padx=(10, 0))
                        status_path_labels.append(path_lbl)
                        
                        # Time label (initially empty)
                        time_lbl = tk.Label(step_container, text="", anchor="w", bg="#1e1e1e", fg="#888", font=("Consolas", 6))
                        time_lbl.pack(side="top", fill="x", padx=(10, 0))
                        status_time_labels.append(time_lbl)
                        
                        # Summary label for step stats (initially empty)
                        summary_lbl = tk.Label(step_container, text="", anchor="w", bg="#1e1e1e", fg="#3498DB", font=("Consolas", 7), wraplength=window_width-60)
                        summary_lbl.pack(side="top", fill="x", padx=(10, 0))
                        status_summary_labels.append(summary_lbl)
                    
                    # Separator
                    sep = tk.Frame(main_frame, height=2, bg="#444")
                    sep.pack(fill="x", padx=10, pady=5)
                    
                    # Individual step buttons
                    buttons_frame = tk.Frame(main_frame, bg="#1e1e1e")
                    buttons_frame.pack(fill="x", padx=10, pady=5)
                    
                    step_buttons = []
                    button_labels = ["Step 1", "Step 2", "Step 3", "Step 4", "Step 5", "Step 6"]
                    
                    def create_step_handler(step_idx):
                        """Create a click handler for individual step button"""
                        def handler():
                            # Check if previous steps are completed
                            if step_idx > 0:
                                for i in range(step_idx):
                                    if not step_completed[i]:
                                        log_activity(f"\n❌ Cannot run {steps[step_idx]} - {steps[i]} must complete first!", "#ff0000")
                                        return
                            
                            # Update overall progress
                            update_overall_progress(step_idx)
                            
                            # Run single step
                            start_step_timer(step_idx)
                            status_labels[step_idx].config(text=f"{steps[step_idx]} - Running ⏳", fg="#1e90ff")
                            log_activity(f"\n{'='*40}", "#ffaa00")
                            log_activity(f"{steps[step_idx]} - STARTED", "#ffaa00")
                            log_activity(f"{'='*40}", "#ffaa00")
                            
                            # Show progress bar for current step only
                            status_win.after(0, lambda: progress_frame.pack_forget())
                            status_win.after(0, lambda: progress_label.config(text=f"{steps[step_idx]} in progress..."))
                            status_win.after(0, lambda: progress_bar.config(value=0))
                            status_win.after(0, lambda: progress_frame.pack(fill="x", padx=10, pady=5))
                            
                            if step_idx == 0:
                                threading.Thread(target=lambda: execute_step_1(step_idx, auto_continue=False), daemon=True).start()
                            elif step_idx == 1:
                                threading.Thread(target=lambda: execute_step_2(step_idx, auto_continue=False), daemon=True).start()
                            elif step_idx == 2:
                                threading.Thread(target=lambda: execute_step_3(step_idx, auto_continue=False), daemon=True).start()
                            elif step_idx == 3:
                                threading.Thread(target=lambda: execute_step_4(step_idx, auto_continue=False), daemon=True).start()
                            elif step_idx == 4:
                                threading.Thread(target=lambda: execute_step_5(step_idx, auto_continue=False), daemon=True).start()
                            elif step_idx == 5:
                                threading.Thread(target=lambda: execute_step_6(step_idx, auto_continue=False), daemon=True).start()
                        return handler
                    
                    for i, btn_label in enumerate(button_labels):
                        btn = tk.Button(buttons_frame, text=btn_label, bg="#2d2d2d", fg="#fff", 
                                       font=("Consolas", 7), relief="flat", padx=5, pady=2, 
                                       cursor="hand2", command=create_step_handler(i))
                        btn.pack(side="left", padx=2, expand=True, fill="x")
                        step_buttons.append(btn)
                    
                    # Tabs: Activity + Details
                    # Overall progress bar at the top
                    overall_progress_frame = tk.Frame(main_frame, bg="#1e1e1e")
                    overall_progress_frame.pack(fill="x", padx=10, pady=(5,5))
                    
                    overall_progress_label = tk.Label(overall_progress_frame, text="Step 0/6 - Ready", 
                                                      bg="#1e1e1e", fg="#aaa", font=("Consolas", 8))
                    overall_progress_label.pack()
                    
                    overall_progress_bar = ttk.Progressbar(overall_progress_frame, length=window_width-40, mode='determinate')
                    overall_progress_bar.pack(pady=2)
                    overall_progress_bar['maximum'] = 6
                    overall_progress_bar['value'] = 0
                    
                    overall_time_label = tk.Label(overall_progress_frame, text="Est. time: calculating...", 
                                                  bg="#1e1e1e", fg="#888", font=("Consolas", 7))
                    overall_time_label.pack()
                    
                    # Activity window content (no label to save space)
                    
                    # Pause/Resume functionality
                    is_paused = [False]
                    
                    # Pause/Resume buttons at top
                    button_frame = tk.Frame(main_frame, bg="#1e1e1e")
                    button_frame.pack(fill="x", padx=10, pady=5)
                    
                    pause_button = tk.Button(button_frame, text="⏸ PAUSE", bg="#ff8800", fg="white", 
                                            font=("Arial", 9, "bold"), relief="flat", cursor="hand2", width=10)
                    pause_button.pack(side="left", padx=(0, 5))
                    
                    resume_button = tk.Button(button_frame, text="▶ RESUME", bg="#00aa00", fg="white", 
                                             font=("Arial", 9, "bold"), relief="flat", cursor="hand2", width=10,
                                             state="disabled")
                    resume_button.pack(side="left")
                    
                    def do_pause():
                        try:
                            is_paused[0] = True
                            self._is_paused_403 = True
                            pause_button.config(state="disabled", bg="#666")
                            resume_button.config(state="normal", bg="#00ff00")
                            log_activity("⏸ PAUSED - Click RESUME to continue", "#ff8800")
                        except Exception as e:
                            log_to_file(f"[Queue] Error pausing: {e}")
                    
                    def do_resume():
                        try:
                            is_paused[0] = False
                            self._is_paused_403 = False
                            pause_button.config(state="normal", bg="#ff8800")
                            resume_button.config(state="disabled", bg="#00aa00")
                            log_activity("▶ RESUMED", "#00ff00")
                        except Exception as e:
                            log_to_file(f"[Queue] Error resuming: {e}")
                    
                    pause_button.config(command=do_pause)
                    resume_button.config(command=do_resume)
                    
                    activity_frame = tk.Frame(main_frame, bg="#1e1e1e")
                    activity_frame.pack(fill="both", expand=True, padx=10, pady=(0,10))
                    
                    activity_text = tk.Text(activity_frame, width=35, bg="#0a0a0a", fg="#00ff00", 
                                           font=("Consolas", 8), wrap="word", relief="flat", padx=6, pady=6)
                    activity_scroll = tk.Scrollbar(activity_frame, command=activity_text.yview)
                    activity_text.config(yscrollcommand=activity_scroll.set)
                    activity_scroll.pack(side="right", fill="y")
                    activity_text.pack(side="left", fill="both", expand=True)
                    
                    # Progress bar for Step 3 (initially hidden)
                    progress_frame = tk.Frame(main_frame, bg="#1e1e1e")
                    progress_label = tk.Label(progress_frame, text="", bg="#1e1e1e", fg="#aaa", font=("Consolas", 7))
                    progress_label.pack()
                    progress_bar = ttk.Progressbar(progress_frame, length=window_width-40, mode='determinate')
                    progress_bar.pack(pady=2)
                    
                    def log_activity(msg, color="#00ff00"):
                        try:
                            # Check if the widget still exists before trying to update it
                            if activity_text.winfo_exists():
                                activity_text.insert("end", msg + "\n", color)
                                activity_text.see("end")
                                activity_text.update()
                        except tk.TclError:
                            # Window was closed, silently ignore
                            pass
                    
                    def open_path(path):
                        """Open file explorer at the given path"""
                        try:
                            if os.path.isfile(path):
                                os.startfile(os.path.dirname(path))
                            elif os.path.isdir(path):
                                os.startfile(path)
                        except Exception as e:
                            log_activity(f"Failed to open: {e}", "#ff0000")
                    
                    def add_path_link(path, label="📁"):
                        """Add a clickable link to open a path"""
                        activity_text.insert("end", f"  {label} ")
                        link_start = activity_text.index("end-1c")
                        activity_text.insert("end", path, "link")
                        link_end = activity_text.index("end-1c")
                        activity_text.tag_config("link", foreground="#00aaff", underline=True)
                        activity_text.tag_bind("link", "<Button-1>", lambda e, p=path: open_path(p))
                        activity_text.tag_bind("link", "<Enter>", lambda e: activity_text.config(cursor="hand2"))
                        activity_text.tag_bind("link", "<Leave>", lambda e: activity_text.config(cursor=""))
                        activity_text.insert("end", "\n")
                    
                    def set_status_path(idx, path, click_handler=None):
                        """Set clickable path next to status label"""
                        filename = os.path.basename(path) if path else ""
                        status_path_labels[idx].config(text=f"📄 {filename}")
                        if click_handler:
                            status_path_labels[idx].bind("<Button-1>", lambda e: click_handler(path))
                    
                    def set_status_time(idx, time_text):
                        """Set time/duration text next to status label"""
                        status_time_labels[idx].config(text=time_text)
                    
                    def set_status_summary(idx, summary_text, color="#3498DB"):
                        """Set summary/stats text under a step"""
                        status_summary_labels[idx].config(text=summary_text, fg=color)
                    
                    def start_step_timer(idx):
                        """Record the start time for a step"""
                        import time
                        step_start_times[idx] = time.time()
                        now = datetime.now().strftime("%H:%M:%S")
                        set_status_time(idx, f"⏱️ Started: {now}")
                    
                    def finish_step_timer(idx):
                        """Calculate and display duration for a step"""
                        import time
                        if idx in step_start_times:
                            duration = time.time() - step_start_times[idx]
                            now = datetime.now().strftime("%H:%M:%S")
                            if duration < 60:
                                duration_text = f"✓ Done: {now} ({duration:.1f}s)"
                            else:
                                mins = int(duration // 60)
                                secs = int(duration % 60)
                                duration_text = f"✓ Done: {now} ({mins}m {secs}s)"
                            set_status_time(idx, duration_text)
                        else:
                            now = datetime.now().strftime("%H:%M:%S")
                            set_status_time(idx, f"✓ Done: {now}")
                    
                    # Average step times (in seconds) for estimation
                    avg_step_times = {
                        0: 5,   # Fetch HTML
                        1: 15,  # Create JSON
                        2: 10,  # Extract Data
                        3: 8,   # Upload
                        4: 20,  # Insert DB
                        5: 15   # Address Match
                    }
                    
                    def update_overall_progress(current_step):
                        """Update overall progress bar and time estimate"""
                        # current_step is now the step that just completed (0-based index)
                        completed = current_step + 1  # Number of completed steps
                        overall_progress_bar['value'] = completed
                        remaining_steps = 6 - completed
                        est_time = sum(avg_step_times[i] for i in range(completed, 6))
                        
                        if est_time < 60:
                            time_str = f"{est_time}s"
                        else:
                            mins = int(est_time // 60)
                            secs = int(est_time % 60)
                            time_str = f"{mins}m {secs}s"
                        
                        overall_progress_label.config(text=f"Step {completed}/6 completed")
                        overall_time_label.config(text=f"Est. time remaining: {time_str}")
                    
                    # Run steps with actual functionality
                    def run_steps(idx=0):
                        # Check if paused before starting next step
                        if is_paused[0]:
                            # Wait and check again
                            status_win.after(500, lambda: run_steps(idx))
                            return
                        
                        if idx >= len(steps):
                            import time as _t
                            # Compute total elapsed time
                            total_elapsed = None
                            try:
                                if workflow_start_time[0] is not None:
                                    total_elapsed = _t.time() - workflow_start_time[0]
                            except Exception:
                                total_elapsed = None
                            # Format total time
                            total_text = ""
                            if total_elapsed is not None:
                                if total_elapsed < 60:
                                    total_text = f" (Total: {int(total_elapsed)}s)"
                                else:
                                    _m = int(total_elapsed // 60)
                                    _s = int(total_elapsed % 60)
                                    total_text = f" (Total: {_m}m {_s}s)"
                            # Persist to stats and update table Summary (Networks)
                            try:
                                job_stats['total_time_sec'] = int(total_elapsed or 0)
                                _update_summary_on_table()
                            except Exception:
                                pass
                            log_activity(f"\n✅ All steps completed!{total_text}", "#00ff00")
                            overall_progress_bar['value'] = 6
                            overall_progress_label.config(text="Step 6/6 - Complete ✅", fg="#00ff00")
                            overall_time_label.config(text=f"All done!{(' ' + total_text.strip()) if total_text else ''}")
                            # Show total workflow time in Step 6 summary
                            try:
                                time_clean = total_text.replace(' (Total: ', '').replace(')', '')
                                set_status_summary(5, f"🏁 Workflow complete! Total time: {time_clean}", "#00ff00")
                            except Exception:
                                pass
                            
                            # Update status in appropriate table (queue_websites or google_places)
                            try:
                                import mysql.connector
                                from datetime import datetime
                                conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                cursor = conn.cursor()
                                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                
                                is_websites = str(table).lower() in ('listing_websites', 'websites')
                                if is_websites:
                                    # For Websites tab, we don't update status (google_places doesn't have status column)
                                    log_to_file(f"[Queue] ✓ Websites tab job {job_id} completed (no status update needed)")
                                else:
                                    # For Networks tab, update queue_websites
                                    cursor.execute("UPDATE queue_websites SET status = %s, processed_at = %s WHERE id = %s", ("done", now_str, job_id))
                                    conn.commit()
                                    log_to_file(f"[Queue] ✓ Updated queue_websites: status='done', processed_at='{now_str}' for job {job_id}")
                                
                                cursor.close()
                                conn.close()
                            except Exception as db_err:
                                log_to_file(f"[Queue] ⚠️ Failed to update status: {db_err}")
                            
                            return
                        
                        # Check if previous steps are completed (for auto-continue)
                        if idx > 0 and not step_completed[idx - 1]:
                            log_activity(f"\n❌ Cannot auto-continue to {steps[idx]} - previous step failed!", "#ff0000")
                            return
                        
                        # Record workflow start time at first step
                        if idx == 0 and workflow_start_time[0] is None:
                            import time as _t
                            workflow_start_time[0] = _t.time()
                        
                        start_step_timer(idx)
                        status_labels[idx].config(text=f"{steps[idx]} - Running ⏳", fg="#1e90ff")
                        log_activity(f"\n{'='*40}", "#ffaa00")
                        log_activity(f"{steps[idx]} - STARTED", "#ffaa00")
                        log_activity(f"{'='*40}", "#ffaa00")
                        
                        # Execute step based on index
                        if idx == 0:  # Step 1: Fetch HTML
                            threading.Thread(target=lambda: execute_step_1(idx), daemon=True).start()
                        elif idx == 1:  # Step 2: Create JSON
                            threading.Thread(target=lambda: execute_step_2(idx), daemon=True).start()
                        elif idx == 2:  # Step 3: Extract Data
                            threading.Thread(target=lambda: execute_step_3(idx), daemon=True).start()
                        elif idx == 3:  # Step 4: Upload
                            threading.Thread(target=lambda: execute_step_4(idx), daemon=True).start()
                        elif idx == 4:  # Step 5: Insert DB
                            threading.Thread(target=lambda: execute_step_5(idx), daemon=True).start()
                        elif idx == 5:  # Step 6: Address Match
                            threading.Thread(target=lambda: execute_step_6(idx), daemon=True).start()
                    
                    def execute_step_1(idx, auto_continue=True):
                        """Step 1: Fetch HTML - Get link and CSS from appropriate table based on current tab"""
                        try:
                            import os
                            status_win.after(0, lambda: log_activity("Starting HTML capture...", "#aaa"))
                            
                            # Determine which table to query based on current tab
                            import mysql.connector
                            conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                            cursor = conn.cursor()
                            
                            # Check if we're on Websites tab
                            is_websites = str(table).lower() in ('listing_websites', 'websites')
                            
                            if is_websites:
                                # Query google_places table for Websites tab
                                cursor.execute("SELECT Website FROM google_places WHERE id = %s", (job_id,))
                                result = cursor.fetchone()
                                cursor.close()
                                conn.close()
                                
                                if not result:
                                    raise Exception(f"Job {job_id} not found in google_places")
                                
                                link = result[0]
                                the_css = None  # Websites don't have CSS selector
                                capture_mode = 'headless'
                            else:
                                # Query queue_websites table for Networks tab
                                cursor.execute("SELECT link, the_css, capture_mode FROM queue_websites WHERE id = %s", (job_id,))
                                result = cursor.fetchone()
                                cursor.close()
                                conn.close()
                                
                                if not result:
                                    raise Exception(f"Job {job_id} not found in queue_websites")
                                
                                link = result[0]
                                the_css = result[1] if len(result) > 1 else None
                                capture_mode = result[2] if len(result) > 2 else 'headless'
                            
                            status_win.after(0, lambda: log_activity(f"  Link: {link}", "#aaa"))
                            if the_css:
                                status_win.after(0, lambda: log_activity(f"  CSS: {the_css}", "#aaa"))
                            status_win.after(0, lambda cm=capture_mode: log_activity(f"  Mode: {cm}", "#aaa"))
                            
                            # Create callback for 403 automation to log to activity window
                            def activity_logger(msg, color="#aaa"):
                                status_win.after(0, lambda m=msg, c=color: log_activity(m, c))
                            
                            # Store the logger in instance for use by _step_capture_html
                            self._activity_logger = activity_logger
                            
                            # Call the existing _step_capture_html method with capture_mode
                            html_file = self._step_capture_html(job_id, link, the_css, table, capture_mode)
                            
                            if html_file and os.path.exists(html_file):
                                status_win.after(0, lambda: log_activity("✅ HTML captured!", "#00ff00"))
                                status_win.after(0, lambda: set_status_path(idx, html_file, open_path))
                                status_win.after(0, lambda: add_path_link(html_file, "📄 HTML"))
                                status_win.after(0, lambda: finish_step(idx, auto_continue))
                            else:
                                # No HTML file found - mark as failed
                                error_msg = "HTML file not found - capture failed"
                                status_win.after(0, lambda: log_activity(f"❌ {error_msg}", "#ff0000"))
                                # Update network status to error
                                network_id = get_network_id()
                                if network_id:
                                    update_db_status(network_id, "error", error_msg)
                                
                                # Update status in appropriate table
                                try:
                                    import mysql.connector
                                    conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                    cursor = conn.cursor()
                                    
                                    is_websites = str(table).lower() in ('listing_websites', 'websites')
                                    if not is_websites:
                                        # Only update queue_websites for Networks tab
                                        cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                        conn.commit()
                                    
                                    cursor.close()
                                    conn.close()
                                except Exception as db_err:
                                    log_to_file(f"[Queue] Failed to update status: {db_err}")
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                                # DO NOT continue to next step
                                return
                        except Exception as e:
                            error_msg = str(e)
                            status_win.after(0, lambda: log_activity(f"❌ Step 1 failed: {error_msg}", "#ff0000"))
                            
                            # Check if it's a 403 error - if so, switch to 'browser' mode and retry (Networks only)
                            is_websites = str(table).lower() in ('listing_websites', 'websites')
                            if not is_websites and '403' in error_msg and 'Forbidden' in error_msg:
                                status_win.after(0, lambda: log_activity(f"🔄 Detected 403 Forbidden - switching to 'browser' mode and retrying...", "#FFA500"))
                                try:
                                    import mysql.connector
                                    conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE queue_websites SET capture_mode = %s WHERE id = %s", ("browser", job_id))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                                    status_win.after(0, lambda: log_activity(f"✓ Updated capture_mode to 'browser' in database", "#27AE60"))
                                    # Retry Step 1 with browser mode
                                    status_win.after(1000, lambda: execute_step_1(idx, auto_continue))
                                    return
                                except Exception as db_err:
                                    status_win.after(0, lambda: log_activity(f"❌ Failed to update capture_mode: {db_err}", "#ff0000"))
                            
                            # Update network status to error
                            network_id = get_network_id()
                            if network_id:
                                update_db_status(network_id, "error", error_msg)
                            
                            # Update status in appropriate table with error message (second location)
                            try:
                                import mysql.connector
                                conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                cursor = conn.cursor()
                                
                                is_websites = str(table).lower() in ('listing_websites', 'websites')
                                if not is_websites:
                                    # Only update queue_websites for Networks tab
                                    cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                    conn.commit()
                                
                                cursor.close()
                                conn.close()
                            except Exception as db_err:
                                log_to_file(f"[Queue] Failed to update status: {db_err}")
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                            # DO NOT continue to next step - stop here
                            return
                    
                    def execute_step_2(idx, auto_continue=True):
                        """Step 2: Create JSON"""
                        try:
                            status_win.after(0, lambda: log_activity("Creating JSON...", "#aaa"))
                            # Determine the expected JSON filename based on table
                            date_str = datetime.now().strftime("%Y-%m-%d")
                            base_captures_dir = os.path.join(os.path.dirname(__file__), "Captures", date_str)
                            
                            # Check if we're on Websites tab to determine subfolder
                            is_websites = str(table).lower() in ('listing_websites', 'websites')
                            subfolder = "Websites" if is_websites else "Networks"
                            prefix = "google_places" if is_websites else "networks"
                            
                            today_captures_dir = os.path.join(base_captures_dir, subfolder)
                            html_path = None
                            json_path = None
                            json_filename = None
                            
                            # Find the HTML file for this job (use actual filename with correct prefix)
                            if os.path.exists(today_captures_dir):
                                expected_html = f"{prefix}_{job_id}.html"
                                html_path = os.path.join(today_captures_dir, expected_html)
                                if os.path.exists(html_path):
                                    json_filename = f"{prefix}_{job_id}.json"
                            
                            if not html_path or not json_filename or not os.path.exists(html_path):
                                error_msg = f"HTML file not found for job {job_id} in {today_captures_dir}"
                                status_win.after(0, lambda: log_activity(f"❌ {error_msg}", "#ff0000"))
                                # Update network status to error
                                network_id = get_network_id()
                                if network_id:
                                    update_db_status(network_id, "error", error_msg)
                                # Update status in appropriate table
                                try:
                                    import mysql.connector
                                    conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                    cursor = conn.cursor()
                                    
                                    is_websites = str(table).lower() in ('listing_websites', 'websites')
                                    if not is_websites:
                                        # Only update queue_websites for Networks tab
                                        cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                        conn.commit()
                                    
                                    cursor.close()
                                    conn.close()
                                except Exception as db_err:
                                    log_to_file(f"[Queue] Failed to update status: {db_err}")
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                                status_win.after(0, lambda: finish_step_timer(idx))
                                return
                            candidate_path = os.path.join(today_captures_dir, json_filename)
                            # Run PHP script headlessly via requests
                            try:
                                import requests
                                import urllib.parse
                                php_url = php_url("process_html_with_openai.php")
                                params = {
                                    "file": html_path,
                                    "model": "gpt-4o-mini",
                                    "method": "local",
                                    "process": "1",
                                    "headless": "1"
                                }
                                encoded_params = urllib.parse.urlencode(params)
                                full_url = f"{php_url}?{encoded_params}"
                                status_win.after(0, lambda u=full_url: log_activity(f"  API: {u}", "#aaa"))
                                status_win.after(0, lambda: log_activity(f"  Triggering PHP (headless)...", "#aaa"))
                                resp = requests.get(full_url, timeout=60)
                                status_win.after(0, lambda: log_activity(f"  PHP response: {resp.status_code}", "#aaa"))
                                if resp.status_code == 200:
                                    status_win.after(0, lambda: log_activity(f"  ✓ PHP processing complete", "#00ff00"))
                                else:
                                    status_win.after(0, lambda: log_activity(f"  ⚠️ PHP returned: {resp.status_code}", "#ffaa00"))
                            except Exception as php_err:
                                status_win.after(0, lambda e=str(php_err): log_activity(f"❌ PHP request failed: {e}", "#ff0000"))
                            # Now wait for the JSON file to be created (poll for up to 30 seconds)
                            import time
                            max_wait = 30  # Maximum 30 seconds
                            waited = 0
                            status_win.after(0, lambda jf=json_filename: log_activity(f"  Waiting for: {jf}", "#aaa"))
                            while waited < max_wait:
                                if os.path.exists(candidate_path) and os.path.isfile(candidate_path):
                                    time.sleep(1)
                                    json_path = candidate_path
                                    break
                                time.sleep(1)
                                waited += 1
                                if waited % 5 == 0:
                                    status_win.after(0, lambda w=waited: log_activity(f"  Still waiting... ({w}s)", "#aaa"))
                            
                            # Try to find the JSON file in TODAY'S folder only and count listings
                            listing_count = 0
                            
                            if json_path and os.path.exists(json_path):
                                # Try to count listings in JSON
                                try:
                                    import json
                                    with open(json_path, 'r', encoding='utf-8') as f:
                                        data = json.load(f)
                                        if isinstance(data, list):
                                            listing_count = len(data)
                                        elif isinstance(data, dict) and 'listings' in data:
                                            listing_count = len(data['listings'])
                                except Exception as parse_err:
                                    status_win.after(0, lambda e=str(parse_err): log_activity(f"  ⚠️ JSON parse error: {e}", "#ff0000"))
                            
                            # Check if we actually have listings
                            if not json_path or not os.path.exists(json_path):
                                # JSON file not found
                                error_msg = f"JSON file not found: {json_filename}"
                                status_win.after(0, lambda em=error_msg: log_activity(f"❌ {em}", "#ff0000"))
                                # Update network status to error
                                network_id = get_network_id()
                                if network_id:
                                    update_db_status(network_id, "error", error_msg)
                                # Update queue_websites status to error
                                try:
                                    import mysql.connector
                                    conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                                except Exception as db_err:
                                    log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                                status_win.after(0, lambda: finish_step_timer(idx))
                                # Don't continue to next step
                                return
                            elif listing_count == 0:
                                # JSON exists but no listings - FAIL
                                error_msg = f"No listings found in JSON"
                                log_to_file(f"[Queue] ❌ {error_msg}")
                                status_win.after(0, lambda em=error_msg: log_activity(f"❌ {em}", "#ff0000"))
                                # Update network status to error
                                network_id = get_network_id()
                                if network_id:
                                    update_db_status(network_id, "error", error_msg)
                                # Update queue_websites status to error
                                try:
                                    import mysql.connector
                                    conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                                except Exception as db_err:
                                    log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌ (0 listings)", fg="#ff0000"))
                                status_win.after(0, lambda: finish_step_timer(idx))
                                return
                            
                            # Check if full_address is present in listings
                            import json as _check_json
                            with open(json_path, 'r', encoding='utf-8') as _check_f:
                                _check_data = _check_json.load(_check_f)
                            
                            if isinstance(_check_data, dict) and 'listings' in _check_data:
                                _check_listings = _check_data.get('listings') or []
                            elif isinstance(_check_data, list):
                                _check_listings = _check_data
                            else:
                                _check_listings = []
                            
                            # Count how many listings have full_address
                            addresses_found = sum(1 for listing in _check_listings if isinstance(listing, dict) and listing.get('full_address'))
                            
                            if addresses_found == 0:
                                error_msg = f"No full_address found in any listing - cannot proceed"
                                log_to_file(f"[Queue] ❌ {error_msg}")
                                status_win.after(0, lambda em=error_msg: log_activity(f"❌ {em}", "#ff0000"))
                                # Update network status to error
                                network_id = get_network_id()
                                if network_id:
                                    update_db_status(network_id, "error", error_msg)
                                # Update queue_websites status to error
                                try:
                                    import mysql.connector
                                    conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                    cursor = conn.cursor()
                                    cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                    conn.commit()
                                    cursor.close()
                                    conn.close()
                                except Exception as db_err:
                                    log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌ (no addresses)", fg="#ff0000"))
                                status_win.after(0, lambda: finish_step_timer(idx))
                                # Don't continue to next step
                                return
                            
                            log_to_file(f"[Queue] ✓ Found full_address in {addresses_found}/{listing_count} listings")
                            status_win.after(0, lambda af=addresses_found, lc=listing_count: log_activity(f"  ✓ Addresses: {af}/{lc}", "#888"))
                            
                            # Success: JSON found with listings and addresses
                            # Capture variables for lambda
                            _json_path = json_path
                            _listing_count = listing_count
                            _json_basename = os.path.basename(json_path)
                            
                            log_to_file(f"[Queue] Setting success status for Step 2...")
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Success ✅ ({_listing_count} listings)", fg="#00ff00"))
                            status_win.after(0, lambda: log_activity(f"✅ JSON created! ({_listing_count} listings)", "#00ff00"))
                            status_win.after(0, lambda: log_activity(f"  📄 {_json_basename}", "#aaa"))
                            
                            log_to_file(f"[Queue] Setting up JSON Fields link...")
                            
                            # Open JSON Field Statistics window when clicked - OPEN POPUP WINDOW
                            def open_json_field_stats(event=None):
                                log_to_file(f"[JSON Stats] Click handler called! Opening POPUP window...")
                                status_win.after(0, lambda: log_activity(f"🔍 Opening JSON Stats Popup...", "#888"))
                                try:
                                    import json as _json
                                    from collections import Counter, defaultdict
                                    
                                    # Load JSON file
                                    log_to_file(f"[JSON Stats] Loading JSON from: {_json_path}")
                                    with open(_json_path, 'r', encoding='utf-8') as _f:
                                        _data = _json.load(_f)
                                    
                                    # Normalize listings array
                                    if isinstance(_data, dict) and 'listings' in _data:
                                        _listings = _data.get('listings') or []
                                    elif isinstance(_data, list):
                                        _listings = _data
                                    else:
                                        _listings = []
                                    
                                    log_to_file(f"[JSON Stats] Found {len(_listings)} listings")
                                    
                                    # Build stats
                                    present_counts = Counter()
                                    filled_counts = Counter()
                                    unique_values = defaultdict(set)
                                    
                                    for it in _listings:
                                        if not isinstance(it, dict):
                                            continue
                                        for k, v in it.items():
                                            present_counts[k] += 1
                                            if v not in (None, "", [], {}):
                                                filled_counts[k] += 1
                                            try:
                                                unique_values[k].add(str(v))
                                            except:
                                                pass
                                    
                                    # Create popup window
                                    popup = tk.Toplevel(status_win)
                                    popup.title(f"📊 JSON Field Statistics - Job {job_id}")
                                    popup.geometry("900x700")
                                    popup.configure(bg="#1e1e1e")
                                    
                                    # Header
                                    header = tk.Frame(popup, bg="#34495E")
                                    header.pack(fill="x")
                                    tk.Label(header, text=f"📊 JSON Field Statistics", 
                                            bg="#34495E", fg="#ECF0F1", 
                                            font=("Segoe UI", 12, "bold")).pack(pady=10)
                                    tk.Label(header, text=f"{len(_listings)} listings • {len(present_counts)} unique keys", 
                                            bg="#34495E", fg="#95A5A6", 
                                            font=("Consolas", 9)).pack(pady=(0,10))
                                    
                                    # Content frame with table + detail panel
                                    content_frame = tk.Frame(popup, bg="#1e1e1e")
                                    content_frame.pack(fill="both", expand=True, padx=10, pady=10)
                                    
                                    # Left: Table
                                    table_frame = tk.Frame(content_frame, bg="#1e1e1e")
                                    table_frame.pack(side="left", fill="both", expand=True)
                                    
                                    cols = ("Key", "Filled", "Total", "Fill %", "Unique")
                                    tree = ttk.Treeview(table_frame, columns=cols, show="headings", height=25)
                                    tree.heading("Key", text="Field Name")
                                    tree.heading("Filled", text="Filled")
                                    tree.heading("Total", text="Total")
                                    tree.heading("Fill %", text="Fill %")
                                    tree.heading("Unique", text="Unique")
                                    
                                    tree.column("Key", width=200, anchor="w")
                                    tree.column("Filled", width=60, anchor="center")
                                    tree.column("Total", width=60, anchor="center")
                                    tree.column("Fill %", width=80, anchor="center")
                                    tree.column("Unique", width=80, anchor="center")
                                    
                                    vsb = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
                                    tree.configure(yscrollcommand=vsb.set)
                                    tree.pack(side="left", fill="both", expand=True)
                                    vsb.pack(side="right", fill="y")
                                    
                                    # Right: Detail panel (shows unique values when clicking a row)
                                    detail_frame = tk.Frame(content_frame, bg="#2c2c2c", width=300)
                                    detail_frame.pack(side="right", fill="both", padx=(10, 0))
                                    detail_frame.pack_propagate(False)
                                    
                                    detail_header = tk.Label(detail_frame, text="Click a field to see values →", 
                                                            bg="#34495E", fg="#95A5A6", 
                                                            font=("Segoe UI", 10), pady=10)
                                    detail_header.pack(fill="x")
                                    
                                    detail_text = tk.Text(detail_frame, bg="#2c2c2c", fg="#ECF0F1", 
                                                         font=("Consolas", 9), wrap="word", 
                                                         padx=10, pady=10, state="disabled")
                                    detail_text.pack(fill="both", expand=True)
                                    
                                    detail_scroll = ttk.Scrollbar(detail_text, orient="vertical", command=detail_text.yview)
                                    detail_text.configure(yscrollcommand=detail_scroll.set)
                                    detail_scroll.pack(side="right", fill="y")
                                    
                                    # Populate
                                    for k in sorted(present_counts.keys(), 
                                                   key=lambda x: (filled_counts.get(x, 0) / max(1, present_counts.get(x, 1)), x), 
                                                   reverse=True):
                                        total = present_counts[k]
                                        filled = filled_counts.get(k, 0)
                                        fill_pct = int((filled / total) * 100) if total > 0 else 0
                                        unique = len(unique_values.get(k, set()))
                                        
                                        if fill_pct >= 90:
                                            tag = "high"
                                        elif fill_pct >= 50:
                                            tag = "med"
                                        else:
                                            tag = "low"
                                        
                                        tree.insert("", "end", 
                                                   values=(k, filled, total, f"{fill_pct}%", unique),
                                                   tags=(tag,))
                                    
                                    tree.tag_configure("high", background="#2d5016", foreground="#a8e063")
                                    tree.tag_configure("med", background="#4a3c0f", foreground="#f9ca24")
                                    tree.tag_configure("low", background="#4a1616", foreground="#eb4d4b")
                                    
                                    # Click handler to show values
                                    def on_tree_click(event):
                                        selection = tree.selection()
                                        if not selection:
                                            return
                                        item = tree.item(selection[0])
                                        field_name = item['values'][0]
                                        
                                        # Update header
                                        detail_header.config(text=f"📋 Values for: {field_name}")
                                        
                                        # Get unique values for this field
                                        values = unique_values.get(field_name, set())
                                        
                                        # Display in detail panel
                                        detail_text.config(state="normal")
                                        detail_text.delete("1.0", "end")
                                        
                                        if not values:
                                            detail_text.insert("1.0", "No values found")
                                        else:
                                            # Show first 100 unique values
                                            sorted_values = sorted(values, key=lambda x: (x == "None", len(x), x))[:100]
                                            for i, val in enumerate(sorted_values, 1):
                                                # Truncate long values
                                                display_val = val if len(val) <= 200 else val[:200] + "..."
                                                detail_text.insert("end", f"{i}. {display_val}\n\n")
                                            
                                            if len(values) > 100:
                                                detail_text.insert("end", f"\n... and {len(values) - 100} more values")
                                        
                                        detail_text.config(state="disabled")
                                    
                                    tree.bind("<ButtonRelease-1>", on_tree_click)
                                    
                                    # Close button
                                    btn_frame = tk.Frame(popup, bg="#1e1e1e")
                                    btn_frame.pack(fill="x", pady=10)
                                    tk.Button(btn_frame, text="Close", command=popup.destroy,
                                             bg="#95A5A6", fg="#fff", font=("Segoe UI", 10),
                                             relief="flat", padx=20, pady=8, cursor="hand2").pack()
                                    
                                    log_to_file(f"[JSON Stats] ✓ Popup window created and shown")
                                    status_win.after(0, lambda: log_activity(f"✓ JSON Stats Popup opened", "#00ff00"))
                                    
                                except Exception as e:
                                    import traceback
                                    error_detail = traceback.format_exc()
                                    log_to_file(f"[JSON Stats] ❌ Failed to open popup: {e}\n{error_detail}")
                                    status_win.after(0, lambda err=str(e): log_activity(f"❌ JSON Stats Error: {err}", "#ff0000"))
                            
                            status_win.after(0, lambda: set_status_path(idx, "JSON Fields", open_json_field_stats))
                            log_to_file(f"[Queue] ✓ set_status_path() called for JSON Fields")
                            status_win.after(0, lambda: add_path_link("JSON Fields", "📊"))
                            log_to_file(f"[Queue] ✓ add_path_link() called for JSON Fields")
                            status_win.after(0, lambda: set_status_summary(idx, f"📄 {_json_basename} • {_listing_count} listings", "#2ECC71"))
                            log_to_file(f"[Queue] ✓ All Step 2 UI elements set")
                            
                            # Stats window: counts per key and value explorer
                            def open_json_stats(path):
                                try:
                                    import json as _json
                                    with open(path, 'r', encoding='utf-8') as _f:
                                        _data = _json.load(_f)
                                except Exception as _e:
                                    status_win.after(0, lambda e=str(_e): log_activity(f"❌ Stats load failed: {e}", "#ff0000"))
                                    return
                                # Normalize listings array
                                if isinstance(_data, dict) and 'listings' in _data:
                                    _listings = _data.get('listings') or []
                                elif isinstance(_data, list):
                                    _listings = _data
                                else:
                                    _listings = []
                                # Build key stats
                                from collections import defaultdict, Counter
                                present_counts = Counter()
                                unique_values = defaultdict(set)
                                for it in _listings:
                                    if not isinstance(it, dict):
                                        continue
                                    for k, v in it.items():
                                        present_counts[k] += 1
                                        try:
                                            # Use simple string form for uniqueness display
                                            unique_values[k].add(str(v))
                                        except Exception:
                                            pass
                                # Create window
                                win = tk.Toplevel(status_win)
                                win.title(f"JSON Stats - Job {job_id}")
                                win.geometry("800x600")
                                win.configure(bg="#1e1e1e")
                                # Layout frames
                                top = tk.Frame(win, bg="#1e1e1e")
                                top.pack(fill="both", expand=True)
                                left = tk.Frame(top, bg="#1e1e1e")
                                left.pack(side="left", fill="both", expand=True, padx=(8,4), pady=8)
                                right = tk.Frame(top, bg="#1e1e1e")
                                right.pack(side="left", fill="both", expand=True, padx=(4,8), pady=8)
                                # Left: keys table
                                cols = ("Key", "Present", "Unique")
                                tree = ttk.Treeview(left, columns=cols, show="headings", height=20)
                                for c in cols:
                                    tree.heading(c, text=c)
                                    tree.column(c, width=200 if c=="Key" else 100, anchor="w")
                                vsb = ttk.Scrollbar(left, orient="vertical", command=tree.yview)
                                tree.configure(yscrollcommand=vsb.set)
                                tree.pack(side="left", fill="both", expand=True)
                                vsb.pack(side="left", fill="y")
                                # Right: values list
                                right_label = tk.Label(right, text="Values (select a key)", bg="#1e1e1e", fg="#ECF0F1", font=("Segoe UI", 10, "bold"))
                                right_label.pack(anchor="w")
                                values_list = tk.Listbox(right, bg="#0d0d0d", fg="#ECF0F1")
                                values_list.pack(fill="both", expand=True)
                                # Buttons
                                btns = tk.Frame(win, bg="#1e1e1e")
                                btns.pack(fill="x", pady=(0,8))
                                def copy_values():
                                    try:
                                        sel = values_list.get(0, "end")
                                        txt = "\n".join(sel)
                                        win.clipboard_clear(); win.clipboard_append(txt)
                                    except Exception:
                                        pass
                                tk.Button(btns, text="Copy Values", command=copy_values, bg="#2d2d2d", fg="#fff", relief="flat").pack(side="left", padx=8)
                                # Populate keys sorted by present count desc
                                for k, cnt in sorted(present_counts.items(), key=lambda kv: (-kv[1], kv[0])):
                                    tree.insert("", "end", values=(k, cnt, len(unique_values.get(k, ()))) )
                                # Selection handler
                                def on_select(_evt=None):
                                    try:
                                        sel = tree.selection()
                                        if not sel: return
                                        item = tree.item(sel[0], "values")
                                        key = item[0]
                                        right_label.config(text=f"Values for {key}")
                                        vals = sorted(unique_values.get(key, []))
                                        values_list.delete(0, "end")
                                        for v in vals:
                                            values_list.insert("end", v)
                                    except Exception:
                                        pass
                                tree.bind("<<TreeviewSelect>>", on_select)
                                def on_double(_evt=None):
                                    on_select()
                                tree.bind("<Double-1>", on_double)
                            
                            # AUTO-OPEN JSON Stats in side panel after Step 2 completes
                            def _auto_open_json_stats():
                                try:
                                    log_to_file(f"[JSON Stats] _auto_open_json_stats() started")
                                    log_to_file(f"[JSON Stats] JSON path: {_json_path}")
                                    import json as _json
                                    log_to_file(f"[JSON Stats] Opening JSON file...")
                                    with open(_json_path, 'r', encoding='utf-8') as _f:
                                        _data = _json.load(_f)
                                    log_to_file(f"[JSON Stats] JSON loaded successfully")
                                    
                                    # Normalize listings array
                                    if isinstance(_data, dict) and 'listings' in _data:
                                        _listings = _data.get('listings') or []
                                    elif isinstance(_data, list):
                                        _listings = _data
                                    else:
                                        _listings = []
                                    
                                    if not _listings:
                                        return
                                    
                                    # Build key stats
                                    from collections import defaultdict, Counter
                                    present_counts = Counter()
                                    unique_values = defaultdict(set)
                                    filled_counts = Counter()  # Count non-empty values
                                    
                                    for it in _listings:
                                        if not isinstance(it, dict):
                                            continue
                                        for k, v in it.items():
                                            present_counts[k] += 1
                                            # Count as "filled" if not None, empty string, or empty list
                                            if v not in (None, "", [], {}):
                                                filled_counts[k] += 1
                                            try:
                                                unique_values[k].add(str(v))
                                            except Exception:
                                                pass
                                    
                                    # Clear and show JSON stats panel on the right
                                    log_to_file(f"[JSON Stats] Clearing existing widgets from panel")
                                    for widget in json_stats_frame.winfo_children():
                                        widget.destroy()
                                    log_to_file(f"[JSON Stats] Panel cleared")
                                    
                                    if not json_stats_visible[0]:
                                        log_to_file(f"[JSON Stats] Panel not visible, adding to PanedWindow...")
                                        # Add the panel to the PanedWindow
                                        screen_w = status_win.winfo_screenwidth()
                                        stats_width = int(screen_w * 0.30)  # 30% width for stats
                                        log_to_file(f"[JSON Stats] Calculated width: {stats_width}px")
                                        paned_window.add(json_stats_frame, width=stats_width)
                                        json_stats_visible[0] = True
                                        log_to_file(f"[JSON Stats] ✓ Panel added to PanedWindow")
                                    else:
                                        log_to_file(f"[JSON Stats] Panel already visible, reusing")
                                    
                                    # Force update and make visible
                                    log_to_file(f"[JSON Stats] Forcing panel update and visibility...")
                                    json_stats_frame.update_idletasks()
                                    paned_window.update()
                                    status_win.update()
                                    
                                    # Debug: Check pane info
                                    try:
                                        panes = paned_window.panes()
                                        log_to_file(f"[JSON Stats] PanedWindow has {len(panes)} panes: {panes}")
                                        log_to_file(f"[JSON Stats] json_stats_frame winfo_width: {json_stats_frame.winfo_width()}")
                                        log_to_file(f"[JSON Stats] json_stats_frame winfo_height: {json_stats_frame.winfo_height()}")
                                        log_to_file(f"[JSON Stats] json_stats_frame winfo_ismapped: {json_stats_frame.winfo_ismapped()}")
                                    except Exception as debug_err:
                                        log_to_file(f"[JSON Stats] Debug error: {debug_err}")
                                    
                                    log_to_file(f"[JSON Stats] Update complete")
                                    
                                    json_stats_frame.configure(bg="#1e1e1e")
                                    
                                    # Header with emoji icon
                                    header = tk.Frame(json_stats_frame, bg="#34495E")
                                    header.pack(fill="x", pady=0)
                                    
                                    # Title with close button
                                    title_frame = tk.Frame(header, bg="#34495E")
                                    title_frame.pack(fill="x")
                                    tk.Label(title_frame, text=f"📊 JSON Field Statistics", 
                                            bg="#34495E", fg="#ECF0F1", 
                                            font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=8)
                                    
                                    # Close button
                                    def close_stats_panel():
                                        paned_window.forget(json_stats_frame)
                                        json_stats_visible[0] = False
                                    
                                    close_btn = tk.Button(title_frame, text="✕", bg="#E74C3C", fg="white", 
                                                         font=("Segoe UI", 10, "bold"), relief="flat", 
                                                         padx=8, pady=2, cursor="hand2", command=close_stats_panel)
                                    close_btn.pack(side="right", padx=10)
                                    
                                    tk.Label(header, text=f"{_listing_count} listings • {len(present_counts)} unique keys", 
                                            bg="#34495E", fg="#95A5A6", 
                                            font=("Consolas", 9)).pack(pady=(0,10))
                                    
                                    # Main content
                                    main = tk.Frame(json_stats_frame, bg="#1e1e1e")
                                    main.pack(fill="both", expand=True, padx=8, pady=8)
                                    
                                    # Treeview with filled/total columns
                                    cols = ("Key", "Filled", "Total", "Fill %", "Unique")
                                    tree = ttk.Treeview(main, columns=cols, show="headings", height=25)
                                    tree.heading("Key", text="Field Name")
                                    tree.heading("Filled", text="Filled")
                                    tree.heading("Total", text="Total")
                                    tree.heading("Fill %", text="Fill %")
                                    tree.heading("Unique", text="Unique")
                                    
                                    tree.column("Key", width=220, anchor="w")
                                    tree.column("Filled", width=70, anchor="center")
                                    tree.column("Total", width=70, anchor="center")
                                    tree.column("Fill %", width=80, anchor="center")
                                    tree.column("Unique", width=80, anchor="center")
                                    
                                    vsb = ttk.Scrollbar(main, orient="vertical", command=tree.yview)
                                    tree.configure(yscrollcommand=vsb.set)
                                    tree.pack(side="left", fill="both", expand=True)
                                    vsb.pack(side="right", fill="y")
                                    
                                    # Populate sorted by fill percentage (descending)
                                    for k in sorted(present_counts.keys(), 
                                                   key=lambda x: (filled_counts.get(x, 0) / max(1, present_counts.get(x, 1)), x), 
                                                   reverse=True):
                                        total = present_counts[k]
                                        filled = filled_counts.get(k, 0)
                                        fill_pct = int((filled / total) * 100) if total > 0 else 0
                                        unique = len(unique_values.get(k, set()))
                                        
                                        # Color-code based on fill percentage
                                        if fill_pct >= 90:
                                            tag = "high"
                                        elif fill_pct >= 50:
                                            tag = "med"
                                        else:
                                            tag = "low"
                                        
                                        tree.insert("", "end", 
                                                   values=(k, filled, total, f"{fill_pct}%", unique),
                                                   tags=(tag,))
                                    
                                    # Configure row colors
                                    tree.tag_configure("high", background="#2d5016", foreground="#a8e063")
                                    tree.tag_configure("med", background="#4a3c0f", foreground="#f9ca24")
                                    tree.tag_configure("low", background="#4a1616", foreground="#eb4d4b")
                                    
                                    # Click handler to show all values for selected field
                                    def on_tree_click(event):
                                        try:
                                            sel = tree.selection()
                                            if not sel:
                                                return
                                            item = tree.item(sel[0], 'values')
                                            field_name = item[0]
                                            
                                            # Create window to show all values for this field
                                            values_win = tk.Toplevel(status_win)
                                            values_win.title(f"All Values: {field_name}")
                                            values_win.geometry("800x600")
                                            values_win.configure(bg="#1e1e1e")
                                            
                                            # Header
                                            header = tk.Frame(values_win, bg="#34495E")
                                            header.pack(fill="x")
                                            tk.Label(header, text=f"📋 All Values for: {field_name}", 
                                                    bg="#34495E", fg="#ECF0F1", 
                                                    font=("Segoe UI", 11, "bold")).pack(pady=10)
                                            
                                            # Table frame
                                            table_frame = tk.Frame(values_win, bg="#1e1e1e")
                                            table_frame.pack(fill="both", expand=True, padx=10, pady=10)
                                            
                                            # Create treeview table with ID and Value columns
                                            cols = ("ID", "Value")
                                            values_table = ttk.Treeview(table_frame, columns=cols, show="headings", height=20)
                                            values_table.heading("ID", text="Listing ID")
                                            values_table.heading("Value", text="Value")
                                            values_table.column("ID", width=100, anchor="center")
                                            values_table.column("Value", width=650, anchor="w")
                                            
                                            # Scrollbars
                                            vsb = ttk.Scrollbar(table_frame, orient="vertical", command=values_table.yview)
                                            hsb = ttk.Scrollbar(table_frame, orient="horizontal", command=values_table.xview)
                                            values_table.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
                                            
                                            values_table.grid(row=0, column=0, sticky="nsew")
                                            vsb.grid(row=0, column=1, sticky="ns")
                                            hsb.grid(row=1, column=0, sticky="ew")
                                            
                                            table_frame.grid_rowconfigure(0, weight=1)
                                            table_frame.grid_columnconfigure(0, weight=1)
                                            
                                            # Populate table with all values for this field from all listings
                                            listing_num = 0
                                            for listing in _listings:
                                                if not isinstance(listing, dict):
                                                    continue
                                                if field_name in listing:
                                                    listing_num += 1
                                                    value = listing.get(field_name)
                                                    # Convert value to string for display
                                                    value_str = str(value) if value is not None else ""
                                                    values_table.insert("", "end", values=(listing_num, value_str))
                                            
                                            # Zebra striping with better contrast
                                            for i, item in enumerate(values_table.get_children()):
                                                if i % 2 == 0:
                                                    values_table.item(item, tags=("evenrow",))
                                                else:
                                                    values_table.item(item, tags=("oddrow",))
                                            
                                            values_table.tag_configure("evenrow", background="#34495E", foreground="#ECF0F1")
                                            values_table.tag_configure("oddrow", background="#2C3E50", foreground="#ECF0F1")
                                            
                                            # Bottom buttons
                                            btn_frame = tk.Frame(values_win, bg="#1e1e1e")
                                            btn_frame.pack(fill="x", pady=8)
                                            
                                            def copy_all():
                                                try:
                                                    # Copy all rows as tab-separated values
                                                    rows = []
                                                    rows.append("Listing ID\tValue")  # Header
                                                    for item in values_table.get_children():
                                                        vals = values_table.item(item, 'values')
                                                        rows.append(f"{vals[0]}\t{vals[1]}")
                                                    content = "\n".join(rows)
                                                    values_win.clipboard_clear()
                                                    values_win.clipboard_append(content)
                                                    copy_btn.config(text="✓ Copied!")
                                                    values_win.after(2000, lambda: copy_btn.config(text="📋 Copy All"))
                                                except Exception:
                                                    pass
                                            
                                            copy_btn = tk.Button(btn_frame, text="📋 Copy All", command=copy_all,
                                                               bg="#3498DB", fg="#fff", font=("Segoe UI", 9),
                                                               relief="flat", padx=12, pady=5, cursor="hand2")
                                            copy_btn.pack(side="left", padx=8)
                                            
                                            tk.Button(btn_frame, text="Close", command=values_win.destroy,
                                                     bg="#95A5A6", fg="#fff", font=("Segoe UI", 9),
                                                     relief="flat", padx=12, pady=5, cursor="hand2").pack(side="right", padx=8)
                                            
                                        except Exception as e:
                                            log_to_file(f"[JSON Stats] Click handler error: {e}")
                                    
                                    tree.bind("<Button-1>", on_tree_click)
                                    
                                    # Bottom buttons
                                    btn_frame = tk.Frame(json_stats_frame, bg="#1e1e1e")
                                    btn_frame.pack(fill="x", pady=8)
                                    
                                    def export_csv():
                                        try:
                                            import csv
                                            from tkinter import filedialog
                                            filename = filedialog.asksaveasfilename(
                                                parent=status_win,
                                                defaultextension=".csv",
                                                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                                                initialfile=f"json_stats_job_{job_id}.csv"
                                            )
                                            if filename:
                                                with open(filename, 'w', newline='', encoding='utf-8') as f:
                                                    writer = csv.writer(f)
                                                    writer.writerow(["Field", "Filled", "Total", "Fill %", "Unique Values"])
                                                    for item in tree.get_children():
                                                        vals = tree.item(item, 'values')
                                                        writer.writerow(vals)
                                                log_to_file(f"[JSON Stats] Exported to {filename}")
                                        except Exception as _exp_err:
                                            log_to_file(f"[JSON Stats] Export failed: {_exp_err}")
                                    
                                    tk.Button(btn_frame, text="📥 Export CSV", command=export_csv,
                                             bg="#3498DB", fg="#fff", font=("Segoe UI", 9),
                                             relief="flat", padx=12, pady=5, cursor="hand2").pack(side="left", padx=8)
                                    
                                    def close_panel():
                                        paned_window.forget(json_stats_frame)
                                        json_stats_visible[0] = False
                                    
                                    tk.Button(btn_frame, text="Close", command=close_panel,
                                             bg="#95A5A6", fg="#fff", font=("Segoe UI", 9),
                                             relief="flat", padx=12, pady=5, cursor="hand2").pack(side="right", padx=8)
                                    
                                    # Add tooltip/status
                                    status_label = tk.Label(btn_frame, text="💡 Green = >90% filled, Yellow = >50%, Red = <50%",
                                                           bg="#1e1e1e", fg="#95A5A6", font=("Consolas", 8))
                                    status_label.pack(side="left", padx=12)
                                    
                                except Exception as _auto_err:
                                    log_to_file(f"[JSON Stats] Auto-open failed: {_auto_err}")
                            
                            # Trigger auto-open after a short delay
                            status_win.after(500, _auto_open_json_stats)
                            
                            # Mark step as completed
                            step_completed[idx] = True
                            # Update job-level stats and table Summary (Networks)
                            try:
                                job_stats['listings'] = int(_listing_count or 0)
                                _update_summary_on_table()
                            except Exception:
                                pass
                            
                            # Don't call finish_step since we already updated the status
                            status_win.after(0, lambda: finish_step_timer(idx))
                            status_win.after(0, lambda: log_activity(f"{steps[idx]} - DONE\n", "#00ff00"))
                            if auto_continue:
                                status_win.after(0, lambda: run_steps(idx + 1))
                        except Exception as e:
                            error_msg = str(e)
                            status_win.after(0, lambda: log_activity(f"❌ Step 2 failed: {error_msg}", "#ff0000"))
                            # Update network status to error
                            network_id = get_network_id()
                            if network_id:
                                update_db_status(network_id, "error", error_msg)
                            # Update queue_websites status to error with message
                            try:
                                import mysql.connector
                                conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                cursor = conn.cursor()
                                cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                            except Exception as db_err:
                                log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                            # DO NOT continue to next step - stop here
                            return
                    
                    def execute_step_3(idx, auto_continue=True):
                        """Step 3: Extract Data (download images) with progress bar"""
                        try:
                            # Download to thumbnails folder
                            thumbnails_dir = os.path.join(os.path.dirname(__file__), "Captures", "thumbnails")
                            os.makedirs(thumbnails_dir, exist_ok=True)
                            
                            status_win.after(0, lambda: set_status_path(idx, thumbnails_dir, open_path))
                            status_win.after(0, lambda: log_activity("Downloading images...", "#aaa"))
                            status_win.after(0, lambda: progress_frame.pack(fill="x", padx=10, pady=5))
                            status_win.after(0, lambda: add_path_link(thumbnails_dir, "📁 Folder"))
                            
                            # Call actual extract step (downloads images in background)
                            self._start_job_step(job_id, table, "manual_match")
                            
                            # Estimate time and show progress
                            estimated_time = 30  # seconds
                            status_win.after(0, lambda: progress_label.config(text=f"Est: ~{estimated_time}s"))
                            
                            # Wait for images to be downloaded and count them
                            import time
                            max_wait = 60  # Wait up to 60 seconds
                            waited = 0
                            image_count = 0
                            
                            while waited < max_wait:
                                time.sleep(2)
                                waited += 2
                                
                                # Check if thumbnails directory has images
                                if os.path.exists(thumbnails_dir):
                                    current_count = len([f for f in os.listdir(thumbnails_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))])
                                    if current_count > 0:
                                        # Wait a bit more to make sure all images are downloaded
                                        time.sleep(3)
                                        image_count = len([f for f in os.listdir(thumbnails_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))])
                                        break
                            
                            # If no images downloaded, skip Steps 3 and 4, go directly to Step 5
                            if image_count == 0:
                                status_win.after(0, lambda: log_activity("⚠️ No images to download, skipping to Step 5...", "#FFA500"))
                                status_win.after(0, lambda: progress_frame.pack_forget())
                                status_win.after(0, lambda: set_status_summary(idx, "⊘ Skipped (no images)", "#FFA500"))
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Skipped ⊘", fg="#FFA500"))
                                
                                # Mark Step 3 as completed (skipped)
                                status_win.after(0, lambda: finish_step(idx, auto_continue=False))
                                
                                # Skip Step 4 (Upload) as well since there are no images to upload
                                step_4_idx = idx + 1
                                if step_4_idx < len(steps):
                                    status_win.after(0, lambda: log_activity("⚠️ Skipping Step 4 (Upload) - no images", "#FFA500"))
                                    status_win.after(0, lambda: set_status_summary(step_4_idx, "⊘ Skipped (no images)", "#FFA500"))
                                    status_win.after(0, lambda: status_labels[step_4_idx].config(text=f"{steps[step_4_idx]} - Skipped ⊘", fg="#FFA500"))
                                    status_win.after(0, lambda: finish_step(step_4_idx, auto_continue=False))
                                
                                # Continue to Step 5 (Insert DB)
                                step_5_idx = idx + 2
                                if step_5_idx < len(steps):
                                    status_win.after(100, lambda: run_steps(step_5_idx, True))
                                return
                            
                            _image_count = image_count
                            status_win.after(0, lambda: log_activity(f"✅ Downloaded {_image_count} images!", "#00ff00"))
                            status_win.after(0, lambda: progress_frame.pack_forget())
                            status_win.after(0, lambda: set_status_summary(idx, f"📥 {_image_count} images downloaded", "#2ECC71"))
                            # Update stats and table Summary (Networks)
                            try:
                                job_stats['images'] = int(_image_count or 0)
                                _update_summary_on_table()
                            except Exception:
                                pass
                            status_win.after(0, lambda: finish_step(idx, auto_continue))
                            
                        except Exception as e:
                            error_msg = str(e)
                            status_win.after(0, lambda: log_activity(f"❌ Step 3 failed: {error_msg}", "#ff0000"))
                            # Update network status to error
                            network_id = get_network_id()
                            if network_id:
                                update_db_status(network_id, "error", error_msg)
                            # Update queue_websites status to error with message
                            try:
                                import mysql.connector
                                conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                cursor = conn.cursor()
                                cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                            except Exception as db_err:
                                log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                            status_win.after(0, lambda: progress_frame.pack_forget())
                            # DO NOT continue to next step - stop here
                            return
                    
                    def execute_step_4(idx, auto_continue=True):
                        """Step 4: Upload with integrated progress"""
                        try:
                            status_win.after(0, lambda: log_activity("Connecting to server...", "#aaa"))
                            status_win.after(0, lambda: progress_frame.pack(fill="x", padx=10, pady=5))
                            
                            # Get images to upload from thumbnails folder
                            thumbnails_dir = os.path.join(os.path.dirname(__file__), "Captures", "thumbnails")
                            
                            if not os.path.exists(thumbnails_dir):
                                raise Exception("Thumbnails folder not found - run Step 3 first")
                            
                            # Get list of image files
                            image_files = []
                            for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
                                import glob
                                image_files.extend(glob.glob(os.path.join(thumbnails_dir, ext)))
                            
                            total_images = len(image_files)
                            
                            if total_images == 0:
                                raise Exception("No images found - run Step 3 first")
                            
                            status_win.after(0, lambda: log_activity(f"Found {total_images} images to upload", "#aaa"))
                            
                            # Set up progress tracking
                            uploaded = [0]
                            skipped = [0]
                            failed = [0]
                            start_time = [__import__('time').time()]
                            
                            def update_upload_progress(current, total, filename, status_type, message):
                                """Callback to update progress in Activity Window"""
                                if status_type == "uploading":
                                    status_win.after(0, lambda: progress_label.config(text=f"Uploading: {filename} ({current}/{total})"))
                                    status_win.after(0, lambda: progress_bar.config(value=current, maximum=total))
                                elif status_type == "uploaded":
                                    uploaded[0] += 1
                                    status_win.after(0, lambda: log_activity(f"✓ {filename}", "#2ECC71"))
                                elif status_type == "skipped":
                                    skipped[0] += 1
                                    status_win.after(0, lambda: log_activity(f"⊘ Skipped: {filename} (exists)", "#95A5A6"))
                                elif status_type == "failed":
                                    failed[0] += 1
                                    status_win.after(0, lambda: log_activity(f"✗ Failed: {filename}", "#E74C3C"))
                                
                                # Update ETA
                                elapsed = __import__('time').time() - start_time[0]
                                if current > 0:
                                    avg_time = elapsed / current
                                    remaining = total - current
                                    eta_seconds = int(avg_time * remaining)
                                    if eta_seconds < 60:
                                        eta_text = f"ETA: {eta_seconds}s"
                                    else:
                                        minutes = eta_seconds // 60
                                        seconds = eta_seconds % 60
                                        eta_text = f"ETA: {minutes}m {seconds}s"
                                    status_win.after(0, lambda: progress_label.config(text=f"{filename} ({current}/{total}) - {eta_text}"))
                            
                            # Run upload in background thread
                            def run_upload():
                                try:
                                    # Call the upload function with progress callback
                                    self._step_process_db_with_progress(job_id, update_upload_progress)
                                    
                                    # Upload complete
                                    _uploaded = uploaded[0]
                                    _skipped = skipped[0]
                                    _failed = failed[0]
                                    elapsed = __import__('time').time() - start_time[0]
                                    
                                    if elapsed < 60:
                                        elapsed_text = f"{int(elapsed)}s"
                                    else:
                                        minutes = int(elapsed / 60)
                                        seconds = int(elapsed % 60)
                                        elapsed_text = f"{minutes}m {seconds}s"
                                    
                                    status_win.after(0, lambda: log_activity(f"✅ Upload complete! Uploaded: {_uploaded}, Skipped: {_skipped}, Failed: {_failed} (Time: {elapsed_text})", "#00ff00"))
                                    status_win.after(0, lambda: progress_frame.pack_forget())
                                    status_win.after(0, lambda: set_status_summary(idx, f"📤 Uploaded: {_uploaded} • Skipped: {_skipped} • Failed: {_failed} • {elapsed_text}", "#2ECC71"))
                                    # Update stats and table Summary (Networks)
                                    try:
                                        job_stats['uploaded'] = int(_uploaded or 0)
                                        job_stats['skipped'] = int(_skipped or 0)
                                        job_stats['failed'] = int(_failed or 0)
                                        _update_summary_on_table()
                                    except Exception:
                                        pass
                                    status_win.after(0, lambda: finish_step(idx, auto_continue))
                                    
                                except Exception as e:
                                    status_win.after(0, lambda: log_activity(f"❌ Upload failed: {e}", "#ff0000"))
                                    status_win.after(0, lambda: progress_frame.pack_forget())
                                    status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                            
                            threading.Thread(target=run_upload, daemon=True).start()
                            
                        except Exception as e:
                            error_msg = str(e)
                            status_win.after(0, lambda: log_activity(f"❌ Step 4 failed: {error_msg}", "#ff0000"))
                            # Update network status to error
                            network_id = get_network_id()
                            if network_id:
                                update_db_status(network_id, "error", error_msg)
                            # Update queue_websites status to error with message
                            try:
                                import mysql.connector
                                conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                cursor = conn.cursor()
                                cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                            except Exception as db_err:
                                log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                            status_win.after(0, lambda: progress_frame.pack_forget())
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                            # DO NOT continue to next step - stop here
                            return
                    
                    def execute_step_5(idx, auto_continue=True):
                        """Step 5: Insert DB (embedded details tab)"""
                        try:
                            status_win.after(0, lambda: log_activity("Inserting to DB...", "#aaa"))
                            # Load JSON listings - check both Networks and Websites folders
                            from datetime import datetime as _dt
                            date_str = _dt.now().strftime("%Y-%m-%d")
                            
                            # Determine which subfolder and prefix based on table
                            is_websites = str(table).lower() in ('listing_websites', 'websites')
                            if is_websites:
                                subfolder = "Websites"
                                prefix = "google_places"
                            else:
                                subfolder = "Networks"
                                prefix = "networks"
                            
                            json_path = BASE_DIR / date_str / subfolder / f"{prefix}_{job_id}.json"
                            
                            if not json_path.exists():
                                # Search only in the current tab's folder
                                pattern = str(BASE_DIR / "*" / subfolder / f"{prefix}_{job_id}.json")
                                matching = __import__('glob').glob(pattern)
                                if matching:
                                    from pathlib import Path as _Path
                                    json_path = _Path(max(matching, key=lambda p: os.path.getmtime(p)))
                            
                            listings = []
                            try:
                                with open(json_path, "r", encoding="utf-8") as f:
                                    listings = json.load(f)
                            except Exception as _e:
                                status_win.after(0, lambda: log_activity(f"❌ Failed to load JSON: {_e}", "#ff0000"))
                                return

                            def db_thread():
                                import time as _time
                                try:
                                    import mysql.connector as _mysql
                                except Exception as _ie:
                                    status_win.after(0, lambda: log_activity("❌ mysql-connector-python not installed", "#ff0000"))
                                    return
                                
                                try:
                                    status_win.after(0, lambda: log_activity(f"Processing {len(listings)} listings...", "#aaa"))
                                    # Connect
                                    conn = None
                                    cursor = None
                                    for attempt in range(1, 4):
                                        try:
                                            conn = _mysql.connect(
                                                host='localhost', user='local_uzr', password='fuck',
                                                database='offta', port=3306, connection_timeout=10, use_pure=True
                                            )
                                            try:
                                                conn.autocommit = True
                                            except Exception:
                                                pass
                                            cursor = conn.cursor(buffered=True)
                                            cursor.execute("SELECT 1")
                                            cursor.fetchone()
                                            break
                                        except Exception as ce:
                                            status_win.after(0, lambda: log_activity(f"DB connect failed (attempt {attempt}/3): {ce}", "#ff0000"))
                                            _time.sleep(2 * attempt)
                                    if cursor is None:
                                        status_win.after(0, lambda: log_activity("❌ Could not connect to DB.", "#ff0000"))
                                        return

                                    # Helpers (lightweight copies)
                                    def to_int(val, default=0):
                                        try:
                                            if val is None:
                                                return default
                                            if isinstance(val, int):
                                                return int(val)
                                            if isinstance(val, float):
                                                return int(round(val))
                                            s = str(val)
                                            digits = ''.join(ch for ch in s if ch.isdigit())
                                            return int(digits) if digits else default
                                        except Exception:
                                            return default

                                    def norm_img_urls(value):
                                        if isinstance(value, list):
                                            return ",".join([str(x).strip() for x in value if str(x).strip()])
                                        return str(value or "").strip()

                                    def to_num_str(val, allow_decimal=False, default="0"):
                                        try:
                                            if val is None:
                                                return default
                                            s = str(val)
                                            if allow_decimal:
                                                cleaned = ''.join(ch for ch in s if (ch.isdigit() or ch == '.'))
                                                parts = cleaned.split('.')
                                                if len(parts) > 2:
                                                    cleaned = parts[0] + '.' + ''.join(parts[1:])
                                                return cleaned if cleaned else default
                                            else:
                                                digits = ''.join(ch for ch in s if ch.isdigit())
                                                return digits if digits else default
                                        except Exception:
                                            return default

                                    new_c = 0
                                    price_c = 0
                                    inactive_c = 0
                                    processed = 0
                                    start = _time.time()
                                    current_urls = set()
                                    current_fa = set()

                                    # If no listings, deactivate all active rows for this network
                                    if not listings:
                                        try:
                                            cursor.execute(
                                                "SELECT id FROM apartment_listings WHERE active='yes' AND network_id=%s",
                                                (int(job_id),)
                                            )
                                            rows = cursor.fetchall() or []
                                            for (lid,) in rows:
                                                cursor.execute("UPDATE apartment_listings SET active='no', time_updated=NOW() WHERE id=%s", (lid,))
                                                inactive_c += 1
                                            status_win.after(0, lambda: log_activity(f"🧹 Marked {inactive_c} inactive for network_{job_id} (no listings in JSON)", "#aaa"))
                                        except Exception as _de:
                                            status_win.after(0, lambda: log_activity(f"❌ Deactivation error: {_de}", "#ff0000"))
                                        # Finalize summary for empty JSON case
                                        _sum_text = f"✅ Insert DB done! New: {new_c}, Price Δ: {price_c}, Inactive: {inactive_c}, Total: 0"
                                        status_win.after(0, lambda: set_status_summary(idx, _sum_text, "#2ECC71"))
                                        return

                                    for listing in listings:
                                        full_address = listing.get("full_address") or listing.get("address") or ""
                                        price = to_int(listing.get("price"), 0)
                                        bedrooms = to_num_str(listing.get("bedrooms"))
                                        bathrooms = to_num_str(listing.get("bathrooms"), allow_decimal=True)
                                        sqft = to_num_str(listing.get("sqft"))
                                        description = listing.get("description") or ""
                                        img_urls = norm_img_urls(listing.get("img_urls") or listing.get("img_url") or "")
                                        available = listing.get("available") or ""
                                        available_date = None
                                        building_name = listing.get("building_name") or listing.get("Building_Name") or None
                                        city = listing.get("city") or None
                                        state = listing.get("state") or None
                                        listing_website = listing.get("listing_website") or listing.get("url") or listing.get("link") or None
                                        listing_id_from_json = listing.get("listing_id") or None

                                        if listing_website:
                                            try:
                                                from urllib.parse import urlparse as _urlparse
                                                dom = _urlparse(listing_website).netloc
                                            except Exception:
                                                dom = None
                                            if listing_website:
                                                current_urls.add(listing_website)
                                        if full_address:
                                            current_fa.add(full_address)

                                        # Prefer by website, else by full_address
                                        existing = None
                                        if listing_website:
                                            cursor.execute("SELECT id, price, active FROM apartment_listings WHERE listing_website = %s", (listing_website,))
                                            existing = cursor.fetchone()
                                        if not existing and full_address:
                                            cursor.execute("SELECT id, price, active FROM apartment_listings WHERE full_address = %s", (full_address,))
                                            existing = cursor.fetchone()

                                        if existing:
                                            listing_id_db, old_price, _act = existing
                                            if (old_price or 0) != (price or 0):
                                                try:
                                                    change_time = _dt.now().strftime('%Y-%m-%d %H:%M:%S')
                                                    change_date = _dt.now().strftime('%Y-%m-%d')
                                                    # Use INSERT ... ON DUPLICATE KEY UPDATE to ensure only one entry per day
                                                    cursor.execute(
                                                        """
                                                        INSERT INTO apartment_listings_price_changes
                                                        (apartment_listings_id, new_price, time)
                                                        VALUES (%s, %s, %s)
                                                        ON DUPLICATE KEY UPDATE new_price = %s, time = %s
                                                        """,
                                                        (listing_id_db, str(price), change_time, str(price), change_time)
                                                    )
                                                except Exception:
                                                    pass
                                                price_c += 1
                                                status_line = f"💰 PRICE CHANGE: {(full_address or listing_website)[:60]} ({old_price} → {price})"
                                            else:
                                                status_line = f"✓ UPDATED: {(full_address or listing_website)[:60]}"
                                            cursor.execute(
                                                """
                                                UPDATE apartment_listings
                                                SET bedrooms=%s, bathrooms=%s, sqft=%s,
                                                    description=%s, img_urls=%s, available=%s, available_date=%s,
                                                    time_updated=NOW(), active='yes', network_id=%s, listing_id=%s
                                                WHERE id=%s
                                                """,
                                                (bedrooms, bathrooms, sqft, description, img_urls, available, available_date, int(job_id), listing_id_from_json, listing_id_db)
                                            )
                                        else:
                                            cursor.execute(
                                                """
                                                INSERT INTO apartment_listings
                                                (active, bedrooms, bathrooms, sqft, price, img_urls, available, available_date,
                                                 description, Building_Name, full_address, city, state, listing_website,
                                                 time_created, time_updated, network_id, listing_id)
                                                VALUES ('yes', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s, %s)
                                                """,
                                                (bedrooms, bathrooms, sqft, price, img_urls, available, available_date,
                                                 description, building_name, full_address, city, state, listing_website, int(job_id), listing_id_from_json)
                                            )
                                            new_c += 1
                                            status_line = f"✨ NEW: {(full_address or listing_website or 'unknown')[:60]} ({price})"

                                        status_win.after(0, lambda: log_activity(status_line, "#aaa"))
                                        processed += 1

                                    # Deactivate not-present
                                    try:
                                        cursor.execute(
                                            "SELECT id, listing_website, full_address FROM apartment_listings WHERE active='yes' AND network_id=%s",
                                            (int(job_id),)
                                        )
                                        rows = cursor.fetchall() or []
                                        deactivated_here = 0
                                        for lid, url, fa in rows:
                                            present = (url and url in current_urls) or (fa and fa in current_fa)
                                            if not present:
                                                cursor.execute("UPDATE apartment_listings SET active='no', time_updated=NOW() WHERE id=%s", (lid,))
                                                inactive_c += 1
                                                deactivated_here += 1
                                        status_win.after(0, lambda: log_activity(f"🧹 Marked {deactivated_here} inactive for network_{job_id}", "#aaa"))
                                    except Exception:
                                        pass

                                    # Final statistics summary
                                    _new_c = new_c
                                    _price_c = price_c
                                    _inactive_c = inactive_c
                                    _total = len(listings)
                                    _sum_text = f"✅ Insert DB done! New: {_new_c}, Price Δ: {_price_c}, Inactive: {_inactive_c}, Total: {_total}"
                                    status_win.after(0, lambda: log_activity(_sum_text, "#00ff00"))
                                    status_win.after(0, lambda: set_status_summary(idx, f"💾 New: {_new_c} • Price Δ: {_price_c} • Inactive: {_inactive_c} • Total: {_total}", "#2ECC71"))
                                    try:
                                        job_stats['new'] = int(_new_c or 0)
                                        job_stats['price_changes'] = int(_price_c or 0)
                                        job_stats['inactive'] = int(_inactive_c or 0)
                                        _update_summary_on_table()
                                    except Exception:
                                        pass
                                    
                                    # Insert stats into network_daily_stats (BEFORE closing connection)
                                    try:
                                        log_to_file(f"[Insert DB] Inserting stats for job {job_id}: price_changes={_price_c}, added={_new_c}, subtracted={_inactive_c}, total={_total}")
                                        cursor.execute(
                                            "INSERT INTO network_daily_stats (network_id, date, price_changes, apartments_added, apartments_subtracted, total_listings) "
                                            "VALUES (%s, CURDATE(), %s, %s, %s, %s) "
                                            "ON DUPLICATE KEY UPDATE price_changes=%s, apartments_added=%s, apartments_subtracted=%s, total_listings=%s",
                                            (int(job_id), _price_c, _new_c, _inactive_c, _total, _price_c, _new_c, _inactive_c, _total)
                                        )
                                        conn.commit()
                                        log_to_file(f"[Insert DB] ✅ Stats successfully inserted for job {job_id}")
                                        _stats_msg = "✅ Stats saved to network_daily_stats"
                                        status_win.after(0, lambda msg=_stats_msg: log_activity(msg, "#2ECC71"))
                                    except Exception as stats_err:
                                        _err_msg = str(stats_err)
                                        log_to_file(f"[Insert DB] ❌ Stats insert failed for job {job_id}: {_err_msg}")
                                        status_win.after(0, lambda msg=_err_msg: log_activity(f"⚠️ Stats insert failed: {msg}", "#ffaa00"))
                                    
                                    # Close connection AFTER stats insert
                                    try:
                                        cursor.close()
                                        conn.close()
                                    except Exception:
                                        pass
                                    status_win.after(0, lambda: finish_step(idx, auto_continue))

                                except Exception as e:
                                    error_msg = str(e)
                                    status_win.after(0, lambda: log_activity(f"❌ Step 5 failed: {error_msg}", "#ff0000"))
                                    # Update network status to error
                                    network_id = get_network_id()
                                    if network_id:
                                        update_db_status(network_id, "error", error_msg)
                                    # Update queue_websites status to error with message
                                    try:
                                        import mysql.connector
                                        conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                        cursor = conn.cursor()
                                        cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                        conn.commit()
                                        cursor.close()
                                        conn.close()
                                    except Exception as db_err:
                                        log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                                    status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                                    # DO NOT continue to next step - stop here
                                    return

                            threading.Thread(target=db_thread, daemon=True).start()
                        except Exception as e:
                            error_msg = str(e)
                            status_win.after(0, lambda: log_activity(f"❌ Step 5 failed: {error_msg}", "#ff0000"))
                            # Update network status to error
                            network_id = get_network_id()
                            if network_id:
                                update_db_status(network_id, "error", error_msg)
                            # Update queue_websites status to error with message
                            try:
                                import mysql.connector
                                conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                cursor = conn.cursor()
                                cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                            except Exception as db_err:
                                log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                            # DO NOT continue to next step - stop here
                            return
                    
                    def execute_step_6(idx, auto_continue=True):
                        """Step 6: Address Match with API call count and final status update"""
                        try:
                            status_win.after(0, lambda: log_activity("Matching addresses...", "#aaa"))
                            status_win.after(0, lambda: progress_frame.pack(fill="x", padx=10, pady=5))

                            # Register a callback so the Address Match window can notify completion
                            def _on_address_match_done(new_calls: int):
                                try:
                                    status_win.after(0, lambda: log_activity(f"📞 API calls: {new_calls}", "#3498DB"))
                                    status_win.after(0, lambda: log_activity("✅ Address matching complete!", "#00ff00"))
                                    status_win.after(0, lambda: set_status_summary(idx, f"🗺️ API calls: {new_calls} • Status: done", "#2ECC71"))
                                    # Update stats and table Summary (Networks)
                                    try:
                                        job_stats['api_calls'] = int(new_calls or 0)
                                        _update_summary_on_table()
                                    except Exception:
                                        pass
                                    
                                    # Update queue_websites: status=done, processed_at=NOW, updated_at=NOW
                                    try:
                                        import mysql.connector
                                        from datetime import datetime
                                        conn = mysql.connector.connect(host='localhost', port=3306, user='local_uzr', password='fuck', database='offta', connect_timeout=10)
                                        cursor = conn.cursor()
                                        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        cursor.execute("""
                                            UPDATE queue_websites 
                                            SET status = 'done', processed_at = %s, updated_at = %s
                                            WHERE id = %s
                                        """, (now_str, now_str, job_id))
                                        conn.commit()
                                        cursor.close()
                                        conn.close()
                                        log_to_file(f"[Address Match] Updated queue_websites status to 'done' with timestamps")
                                    except Exception as db_err:
                                        log_to_file(f"[Address Match] Failed to update queue_websites: {db_err}")
                                finally:
                                    status_win.after(0, lambda: progress_frame.pack_forget())
                                    status_win.after(0, lambda: finish_step(idx, auto_continue))

                            try:
                                ADDRESS_MATCH_CALLBACKS[str(job_id)] = _on_address_match_done
                            except Exception:
                                pass

                            # Add clickable link to reopen Address Match window
                            def open_address_window(path=None):
                                try:
                                    from config_helpers import show_address_match_window
                                    show_address_match_window(job_id, status_win, manual_open=True)
                                except Exception as e:
                                    log_to_file(f"Failed to open address match window: {e}")
                            
                            status_win.after(0, lambda: set_status_path(idx, "Address Match", open_address_window))
                            status_win.after(0, lambda: log_activity("🗺️ Address Match", "#3498DB"))
                            
                            # Launch the Address Match UI directly (bypass API)
                            try:
                                from config_helpers import show_address_match_window
                                status_win.after(0, lambda: show_address_match_window(job_id, status_win, manual_open=False))
                                status_win.after(0, lambda: log_activity("✅ Address Match window opened", "#00ff00"))
                            except Exception as open_err:
                                status_win.after(0, lambda err=str(open_err): log_activity(f"❌ Failed to open window: {err}", "#ff0000"))
                                raise
                            # Do not finish here; wait for callback from the Address Match window
                        except Exception as e:
                            error_msg = str(e)
                            status_win.after(0, lambda: log_activity(f"❌ Step 6 failed: {error_msg}", "#ff0000"))
                            # Update network status to error
                            network_id = get_network_id()
                            if network_id:
                                update_db_status(network_id, "error", error_msg)
                            # Update queue_websites status to error with message
                            try:
                                import mysql.connector
                                conn = mysql.connector.connect(host='localhost', port=3306, user='local_uzr', password='fuck', database='offta', connect_timeout=10)
                                cursor = conn.cursor()
                                cursor.execute("UPDATE queue_websites SET status = %s, last_error = %s WHERE id = %s", ("error", error_msg, job_id))
                                conn.commit()
                                cursor.close()
                                conn.close()
                            except Exception as db_err:
                                log_to_file(f"[Queue] Failed to update queue_websites status: {db_err}")
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                            # DO NOT continue to next step - stop here
                            return
                    
                    def finish_step(idx, auto_continue=True):
                        finish_step_timer(idx)
                        status_labels[idx].config(text=f"{steps[idx]} - Success ✅", fg="#00ff00")
                        log_activity(f"{steps[idx]} - DONE\n", "#00ff00")
                        step_completed[idx] = True  # Mark step as completed
                        update_overall_progress(idx)  # Update progress after step completes
                        if auto_continue:
                            run_steps(idx + 1)
                    
                    # Start execution
                    # Format table name for display
                    tab_display = "Extractor→Websites" if str(table).lower() in ('listing_websites', 'websites') else "Extractor→Networks"
                    log_activity(f"Job {job_id} - {tab_display}", "#ffaa00")
                    log_activity(f"Automated workflow\n", "#aaa")
                    run_steps(0)
                    return
                
                # Handle Edit button click (column #12 - ✏️ is at index 11)
                if column == "#12":
                    values = self._queue_tree.item(item, "values")
                    if values and len(values) > 0:
                        # Extract job_id from "▶ 123" format
                        job_id_str = str(values[0]).replace("▶", "").strip()
                        try:
                            job_id = int(job_id_str)
                        except:
                            job_id = job_id_str
                        table = self._current_table.get()
                        log_to_file(f"[Queue] Edit clicked for job {job_id}")
                        self._show_edit_dialog(job_id, table)
                    return
                
                # Handle Link column click (#2) - open in browser
                if column == "#2":
                    values = self._queue_tree.item(item, "values")
                    if values and len(values) > 1:
                        link = values[1]
                        try:
                            import webbrowser
                            webbrowser.open(link)
                            self._queue_status_label.config(text=f"✓ Opened: {link[:50]}...")
                            log_to_file(f"[Queue] Opened link in browser: {link}")
                        except Exception as open_err:
                            log_to_file(f"[Queue] Failed to open link: {open_err}")
                    return
                
                # Handle stats columns (#8=Δ$, #9=+, #10=-, #11=Total) - show apartment listings
                if column in ("#8", "#9", "#10", "#11"):
                    values = self._queue_tree.item(item, "values")
                    if not values or len(values) == 0:
                        return
                    
                    # Extract job_id (network_id)
                    job_id_str = str(values[0]).replace("▶", "").strip()
                    try:
                        network_id = int(job_id_str)
                    except:
                        log_to_file(f"[Queue] Invalid job ID: {job_id_str}")
                        return
                    
                    # Determine filter based on column
                    filter_type = {
                        "#8": "price_changes",  # Δ$ - listings with price changes
                        "#9": "added",          # + - new listings
                        "#10": "subtracted",    # - - inactive listings
                        "#11": "all"            # Total - all listings
                    }[column]
                    
                    self._show_apartment_listings(network_id, filter_type)
                    return
                
                if column in step_map:
                    # Get the job ID from the first column
                    values = self._queue_tree.item(item, "values")
                    log_to_file(f"[Queue] Row values: {values}")
                    
                    if values and len(values) > 0:
                        # Extract job_id from "▶ 123" format
                        job_id_str = str(values[0]).replace("▶", "").strip()
                        try:
                            job_id = int(job_id_str)
                        except:
                            job_id = job_id_str
                        table = self._current_table.get()
                        step = step_map[column]
                        
                        # Validate prerequisites for each step
                        step_text_map = {
                            "#7": 6,   # 2.JSON column (Step 2)
                            "#8": 7,   # 3.Extract column (Step 3)
                            "#9": 8,   # 4.Upload column (Step 4)
                            "#10": 9,   # 5.Insert DB column (Step 5)
                            "#11": 10   # 6.Address Match column (Step 6)
                        }
                        
                        if column in step_text_map:
                            step_text_idx = step_text_map[column]
                            step_text = str(values[step_text_idx]) if len(values) > step_text_idx else ""
                            
                            # Check if step needs previous step
                            if "⊘ Need Step" in step_text:
                                needed_step = step_text.split("Step ")[-1] if "Step " in step_text else "previous"
                                self._queue_status_label.config(text=f"❌ Cannot run: Need to complete Step {needed_step} first")
                                log_to_file(f"[Queue] Step {step} blocked - prerequisite not met: {step_text}")
                                return
                            
                            # Check for warning states
                            if "⚠️ No images" in step_text or "⚠️ Empty" in step_text:
                                self._queue_status_label.config(text=f"❌ Cannot run: {step_text}")
                                log_to_file(f"[Queue] Step {step} blocked - warning state: {step_text}")
                                return
                        
                        # Enhanced logging and console output
                        log_to_file(f"[Queue] ========== STEP CLICK DETECTED ==========")
                        log_to_file(f"[Queue] Column clicked: {column}")
                        log_to_file(f"[Queue] Step mapped to: {step}")
                        log_to_file(f"[Queue] Job ID: {job_id}")
                        log_to_file(f"[Queue] Table: {table}")
                        
                        print(f"\n{'='*80}")
                        print(f"[CLICK] Step column clicked: {column} -> {step}")
                        print(f"[CLICK] Job ID: {job_id}, Table: {table}")
                        print(f"{'='*80}\n")
                        
                        self._queue_status_label.config(text=f"⏳ Running {step} for job {job_id}...")
                        # Immediately show a spinner in the clicked step column for feedback
                        try:
                            vals_list = list(values)
                            # Map step to column index in values tuple (11 columns total now)
                            step_col_index = {
                                'capture_html': 5,   # 1.HTML column
                                'create_json': 6,    # 2.JSON column
                                'manual_match': 7,   # 3.Extract column (download/extract images)
                                'process_db': 8,     # 4.Upload column (upload images to server)
                                'insert_db': 9,       # 5.Insert DB column
                                'address_match': 10   # 6.Address Match column
                            }.get(step)
                            if step_col_index is not None and step_col_index < len(vals_list):
                                vals_list[step_col_index] = '⏳'
                                self._queue_tree.item(item, values=tuple(vals_list))
                                log_to_file(f"[Queue] Spinner set at column index {step_col_index}")
                        except Exception as _e:
                            log_to_file(f"[Queue] Failed to set pending icon: {_e}")
                        
                        # If this is Parcel Step 1 (capture_html), open helper UIs immediately
                        try:
                            if str(current_table).lower() == 'parcel' and step == 'capture_html':
                                # Ensure tracking set exists
                                if not hasattr(self, '_opened_browser_for_job'):
                                    self._opened_browser_for_job = set()
                                # Read current row values
                                values = self._queue_tree.item(item, "values")
                                metro_name = values[3] if len(values) > 3 else None
                                link_url = values[1] if len(values) > 1 else None
                                # Open Empty Parcels window for this metro (main thread)
                                if metro_name and hasattr(self, '_show_empty_parcels_window'):
                                    try:
                                        self._root.after(0, lambda m=metro_name: self._show_empty_parcels_window(m))
                                    except Exception:
                                        pass
                                # Open Chrome docked right for the link
                                if link_url:
                                    try:
                                        url = str(link_url)
                                        if url and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
                                            url = "http://" + url
                                        launch_manual_browser_docked_right(url)
                                        # Record so background step won't duplicate open
                                        try:
                                            self._opened_browser_for_job.add(str(job_id))
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass
                        except Exception as _ui_open_err:
                            log_to_file(f"[Queue] Pre-step UI open failed: {_ui_open_err}")

                        # Start the step in a background thread
                        log_to_file(f"[Queue] Starting background thread for {step}...")
                        threading.Thread(target=self._start_job_step, args=(job_id, table, step), daemon=True).start()
                        log_to_file(f"[Queue] Background thread started")
                else:
                    log_to_file(f"[Queue] Column {column} not in step_map, ignoring")
            except Exception as e:
                log_to_file(f"[Queue] Tree click error: {e}")
                log_exception("Tree click handler")
        
        self._queue_tree.bind("<Button-1>", safe_tree_click, add="+")
        
        # Right-click handler for JSON column (#7 = 2.JSON), Parcel empty-count (#5), and Error status rows
        def safe_tree_right_click(event):
            try:
                # Identify the row and column
                item = self._queue_tree.identify_row(event.y)
                column = self._queue_tree.identify_column(event.x)
                
                table_now = str(self._current_table.get() or '').lower()

                # Case 1: Right-click on error row → show error message popup
                if item:
                    values = self._queue_tree.item(item, "values")
                    if values and len(values) > 6:  # Status is column 6
                        status = str(values[6]).strip().lower()
                        if status == "error":
                            # Extract job_id
                            job_id_str = str(values[0]).replace("▶", "").strip()
                            try:
                                job_id = int(job_id_str)
                            except:
                                job_id = job_id_str
                            
                            # Fetch error message from database
                            try:
                                import mysql.connector
                                conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                                cursor = conn.cursor()
                                cursor.execute("SELECT last_error FROM queue_websites WHERE id = %s", (job_id,))
                                result = cursor.fetchone()
                                cursor.close()
                                conn.close()
                                
                                if result and result[0]:
                                    error_msg = result[0]
                                    # Show error message in popup window
                                    error_win = tk.Toplevel(self._queue_tree)
                                    error_win.title(f"Error Details - Job {job_id}")
                                    error_win.geometry("500x200")
                                    
                                    # Error message text
                                    text_frame = tk.Frame(error_win, bg="#fff")
                                    text_frame.pack(fill="both", expand=True, padx=10, pady=10)
                                    
                                    error_text = tk.Text(text_frame, wrap="word", font=("Segoe UI", 10), bg="#fff", fg="#000")
                                    error_text.pack(fill="both", expand=True)
                                    error_text.insert("1.0", error_msg)
                                    error_text.config(state="disabled")  # Make read-only
                                    
                                    # Copy button
                                    copy_btn = tk.Button(error_win, text="Copy to Clipboard", 
                                                        command=lambda: (self._root.clipboard_clear(),
                                                                       self._root.clipboard_append(error_msg),
                                                                       copy_btn.config(text="✓ Copied!")))
                                    copy_btn.pack(pady=5)
                                    
                                    log_to_file(f"[Queue] Showing error popup for job {job_id}")
                                    return  # Exit after showing error popup
                                else:
                                    log_to_file(f"[Queue] No error message found for job {job_id}")
                            except Exception as db_err:
                                log_to_file(f"[Queue] Failed to fetch error message: {db_err}")

                # Case 2: JSON column (#7) → show JSON summary popup
                if column == "#7" and item:
                    values = self._queue_tree.item(item, "values")
                    if values and len(values) > 0:
                        # Extract job_id from "▶ 123" format
                        job_id_str = str(values[0]).replace("▶", "").strip()
                        try:
                            job_id = int(job_id_str)
                        except:
                            job_id = job_id_str
                        log_to_file(f"[Queue] Right-click on JSON column for job {job_id}")
                        self._show_json_summary_for_job(job_id, table_now)

                # Case 3: Parcel tab, Empty Parcels column (#5) → open addresses-without-parcels window
                if table_now == 'parcel' and column == "#5" and item:
                    values = self._queue_tree.item(item, "values")
                    if values and len(values) >= 4:
                        # Column #4 holds Metro name after parcel display override
                        metro_name = str(values[3] or '').strip()
                        if metro_name and metro_name != '-':
                            log_to_file(f"[Parcel] Right-click on Empty Parcels for metro: {metro_name}")
                            self._show_empty_parcels_window(metro_name)
            except Exception as e:
                log_to_file(f"[Queue] Right-click handler error: {e}")
                log_exception("Tree right-click handler")
        
        self._queue_tree.bind("<Button-3>", safe_tree_right_click, add="+")

        # Double-click handler on Link column (#2): open URL or mailto
        def safe_tree_double_click(event):
            try:
                region = self._queue_tree.identify_region(event.x, event.y)
                if region != "cell":
                    return
                column = self._queue_tree.identify_column(event.x)
                if column != "#2":
                    return
                item = self._queue_tree.identify_row(event.y)
                if not item:
                    return
                values = self._queue_tree.item(item, "values")
                if not values or len(values) < 2:
                    return
                link = str(values[1] or "").strip()
                if not link:
                    return
                table = str(self._current_table.get() or "").lower()
                url = None
                if table == 'accounts' and '@' in link:
                    url = f"mailto:{link}"
                else:
                    # Assume website URL
                    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", link):
                        url = "http://" + link
                    else:
                        url = link
                try:
                    webbrowser.open_new_tab(url)
                    self._queue_status_label.config(text=f"Opened: {url[:60]}...")
                except Exception as open_err:
                    log_to_file(f"[Queue] Failed to open link: {open_err}")
            except Exception as e:
                log_to_file(f"[Queue] Double-click handler error: {e}")
        self._queue_tree.bind("<Double-1>", safe_tree_double_click, add="+")
        
        # Scrollbar
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self._queue_tree.yview)
        self._queue_tree.configure(yscrollcommand=scroll.set)
        self._queue_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        # ============== Parcel: Empty Parcels window ==============
        def _show_empty_parcels_window(metro_name: str):
            log_to_file(f"[EMPTY PARCELS WINDOW] ========== Opening Empty Parcels Window ==========")
            log_to_file(f"[EMPTY PARCELS WINDOW] Metro: {metro_name}")
            try:
                win = tk.Toplevel(self._root)
                win.title(f"Empty Parcels — {metro_name}")
                try:
                    screen_w = self._root.winfo_screenwidth()
                    screen_h = self._root.winfo_screenheight()
                    log_to_file(f"[EMPTY PARCELS WINDOW] Screen size: {screen_w}x{screen_h}")
                except Exception:
                    screen_w, screen_h = 1200, 800
                    log_to_file(f"[EMPTY PARCELS WINDOW] Using default screen size: {screen_w}x{screen_h}")
                # 20% width, full height, top-left corner
                win_w = max(int(screen_w * 0.20), 360)
                win_h = screen_h
                win.geometry(f"{win_w}x{win_h}+0+0")
                win.configure(bg="#2C3E50")
                log_to_file(f"[EMPTY PARCELS WINDOW] Window size: {win_w}x{win_h} at position 0,0")

                header = tk.Frame(win, bg="#34495E")
                header.pack(fill="x")
                title_lbl = tk.Label(header, text=f"Addresses with NULL king_county_parcels_id — {metro_name}",
                         bg="#34495E", fg="#ECF0F1", font=("Segoe UI", 12, "bold"))
                title_lbl.pack(side="left", padx=12, pady=10)

                body = tk.Frame(win, bg="#2C3E50")
                body.pack(fill="both", expand=True)
                log_to_file(f"[EMPTY PARCELS WINDOW] UI components created")

                cols = ("ID", "Address")
                tree = ttk.Treeview(body, columns=cols, show="headings", height=20)
                # Calculate dynamic address column width based on window width
                id_w = 70
                addr_w = max(win_w - id_w - 30, 200)  # subtract scrollbar/margins
                for c, w in zip(cols, (id_w, addr_w)):
                    tree.heading(c, text=c)
                    tree.column(c, width=w, anchor=("w" if c == "Address" else "center"))
                vs = ttk.Scrollbar(body, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=vs.set)
                tree.pack(side="left", fill="both", expand=True)
                vs.pack(side="right", fill="y")

                # Footer with pagination controls
                footer = tk.Frame(win, bg="#2C3E50")
                footer.pack(fill="x")
                status = tk.Label(footer, text="Loading…", bg="#2C3E50", fg="#ECF0F1")
                status.pack(side="left", padx=8, pady=6)
                nav = tk.Frame(footer, bg="#2C3E50")
                nav.pack(side="right", padx=8)
                btn_prev = tk.Button(nav, text="◀ Prev", relief="flat")
                btn_next = tk.Button(nav, text="Next ▶", relief="flat")
                page_lbl = tk.Label(nav, text="Page 1", bg="#2C3E50", fg="#ECF0F1")
                btn_prev.pack(side="left", padx=4, pady=4)
                page_lbl.pack(side="left", padx=4)
                btn_next.pack(side="left", padx=4, pady=4)

                # API link display + copy (wrap for narrow window)
                link_frame = tk.Frame(win, bg="#2C3E50")
                link_frame.pack(fill="x")
                url_label = tk.Label(link_frame, text="", bg="#2C3E50", fg="#95A5A6", justify="left", anchor="w")
                url_label.configure(wraplength=max(win_w - 80, 120))
                url_label.pack(side="left", padx=8, pady=(0,6), fill="x", expand=True)
                def copy_url():
                    try:
                        self._root.clipboard_clear()
                        self._root.clipboard_append(state.get('last_url',''))
                        try: self._root.update()
                        except Exception: pass
                        status.config(text="Link copied to clipboard")
                    except Exception: pass
                copy_btn = tk.Button(link_frame, text="Copy Link", relief="flat", command=copy_url)
                copy_btn.pack(side="right", padx=8, pady=(0,6))

                # Start automation button
                automation_frame = tk.Frame(win, bg="#2C3E50")
                automation_frame.pack(fill="x", padx=8, pady=(0, 8))
                start_btn = tk.Button(automation_frame, text="▶ Start Parcel Capture", 
                                     relief="raised", bg="#27AE60", fg="white", 
                                     font=("Segoe UI", 10, "bold"), cursor="hand2")
                start_btn.pack(fill="x", pady=4)
                
                automation_status = tk.Label(automation_frame, text="", bg="#2C3E50", fg="#ECF0F1", font=("Consolas", 9))
                automation_status.pack(fill="x")

                # Pagination state
                state = { 'page': 1, 'limit': 20, 'has_next': False, 'last_url': '', 'automation_running': False }

                # Automation worker function
                def run_parcel_automation():
                    log_to_file("[PARCEL AUTOMATION] ========== STARTING PARCEL AUTOMATION ==========")
                    log_to_file(f"[PARCEL AUTOMATION] Metro: {metro_name}")
                    
                    try:
                        log_to_file("[PARCEL AUTOMATION] Importing required libraries...")
                        from selenium import webdriver
                        from selenium.webdriver.common.by import By
                        from selenium.webdriver.common.keys import Keys
                        from selenium.webdriver.support.ui import WebDriverWait
                        from selenium.webdriver.support import expected_conditions as EC
                        from selenium.webdriver.chrome.options import Options
                        from selenium.common.exceptions import UnexpectedAlertPresentException, NoAlertPresentException
                        import pyautogui
                        import pytesseract
                        from PIL import Image
                        import cv2
                        import numpy as np
                        log_to_file("[PARCEL AUTOMATION] All libraries imported successfully")
                    except ImportError as ie:
                        log_to_file(f"[PARCEL AUTOMATION] IMPORT ERROR: Missing library {ie.name}")
                        self._root.after(0, lambda: automation_status.config(
                            text=f"Missing library: {ie.name}. Install: pip install selenium pyautogui pytesseract opencv-python"))
                        return

                    # Locate Tesseract OCR executable and validate availability
                    try:
                        tess_path_env = os.environ.get('TESSERACT_PATH')
                        common_paths = [
                            r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
                            r"C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe"
                        ]
                        chosen_path = None
                        if tess_path_env and os.path.exists(tess_path_env):
                            chosen_path = tess_path_env
                            log_to_file(f"[PARCEL AUTOMATION] Using Tesseract from TESSERACT_PATH: {chosen_path}")
                        else:
                            for p in common_paths:
                                if os.path.exists(p):
                                    chosen_path = p
                                    log_to_file(f"[PARCEL AUTOMATION] Found Tesseract at: {chosen_path}")
                                    break
                        if chosen_path:
                            try:
                                pytesseract.pytesseract.tesseract_cmd = chosen_path
                            except Exception as _tess_set_err:
                                log_to_file(f"[PARCEL AUTOMATION] Failed to set pytesseract cmd: {_tess_set_err}")
                        # Validate version (will raise if not callable)
                        try:
                            ver = str(pytesseract.get_tesseract_version())
                            log_to_file(f"[PARCEL AUTOMATION] Tesseract version: {ver}")
                        except Exception as _tess_err:
                            log_to_file(f"[PARCEL AUTOMATION] Tesseract OCR not available: {_tess_err}")
                            self._root.after(0, lambda: automation_status.config(
                                text="Tesseract OCR not found. Install from https://github.com/UB-Mannheim/tesseract/wiki"))
                            state['automation_running'] = False
                            self._root.after(0, lambda: start_btn.config(state="normal", text="▶ Start Parcel Capture"))
                            return
                    except Exception as _tess_outer:
                        log_to_file(f"[PARCEL AUTOMATION] Tesseract check failed: {_tess_outer}")
                        self._root.after(0, lambda: automation_status.config(
                            text="Tesseract check failed. See debug log."))
                        state['automation_running'] = False
                        self._root.after(0, lambda: start_btn.config(state="normal", text="▶ Start Parcel Capture"))
                        return

                    state['automation_running'] = True
                    self._root.after(0, lambda: start_btn.config(state="disabled", text="⏸ Running..."))
                    log_to_file("[PARCEL AUTOMATION] Automation state set to running")
                    
                    # Create output folder
                    output_dir = Path(r"C:\Users\dokul\Desktop\robot\th_poller\Captures\parcels")
                    output_dir.mkdir(parents=True, exist_ok=True)
                    log_to_file(f"[PARCEL AUTOMATION] Output directory created/verified: {output_dir}")
                    
                    # Get all addresses from current tree view
                    addresses = []
                    def collect_addresses():
                        for item in tree.get_children():
                            vals = tree.item(item, 'values') or []
                            if len(vals) >= 2:
                                addresses.append({
                                    'id': vals[0],
                                    'address': vals[1]
                                })
                    self._root.after(0, collect_addresses)
                    time.sleep(0.5)  # Let UI update
                    
                    log_to_file(f"[PARCEL AUTOMATION] Collected {len(addresses)} addresses from UI")
                    if addresses:
                        log_to_file(f"[PARCEL AUTOMATION] First address: ID={addresses[0].get('id')}, Address={addresses[0].get('address')}")
                    
                    if not addresses:
                        log_to_file("[PARCEL AUTOMATION] ERROR: No addresses to process")
                        self._root.after(0, lambda: automation_status.config(text="No addresses to process"))
                        state['automation_running'] = False
                        self._root.after(0, lambda: start_btn.config(state="normal", text="▶ Start Parcel Capture"))
                        return
                    
                    # Use the full King County parcel viewer link
                    parcel_link = "https://gismaps.kingcounty.gov/parcelviewer2/"
                    log_to_file(f"[PARCEL AUTOMATION] Using parcel link: {parcel_link}")
                    
                    # Setup Chrome with existing profile or new instance
                    chrome_options = Options()
                    chrome_options.add_argument("--start-maximized")
                    log_to_file("[PARCEL AUTOMATION] Chrome options configured: --start-maximized")
                    
                    driver = None
                    try:
                        # Try common Chrome paths
                        log_to_file("[PARCEL AUTOMATION] Searching for Chrome executable...")
                        chrome_paths = [
                            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
                        ]
                        chrome_bin = None
                        for p in chrome_paths:
                            if os.path.exists(p):
                                chrome_bin = p
                                log_to_file(f"[PARCEL AUTOMATION] Chrome found at: {chrome_bin}")
                                break
                        if chrome_bin:
                            chrome_options.binary_location = chrome_bin
                        else:
                            log_to_file("[PARCEL AUTOMATION] WARNING: Chrome not found in standard locations, using system default")
                        
                        log_to_file("[PARCEL AUTOMATION] Launching Chrome WebDriver...")
                        driver = webdriver.Chrome(options=chrome_options)
                        log_to_file("[PARCEL AUTOMATION] Chrome WebDriver started successfully")
                        
                        log_to_file(f"[PARCEL AUTOMATION] Navigating to: {parcel_link}")
                        driver.get(parcel_link)
                        log_to_file("[PARCEL AUTOMATION] Waiting 3 seconds for page load...")
                        time.sleep(3)  # Wait for page load
                        log_to_file("[PARCEL AUTOMATION] Page loaded, ready to process addresses")
                        
                        results = []
                        total = len(addresses)
                        log_to_file(f"[PARCEL AUTOMATION] Starting processing loop for {total} addresses")
                        
                        for idx, addr_data in enumerate(addresses, 1):
                            if not state.get('automation_running'):
                                log_to_file("[PARCEL AUTOMATION] Automation stopped by user")
                                break
                            
                            address = addr_data['address']
                            addr_id = addr_data['id']
                            
                            log_to_file(f"[PARCEL AUTOMATION] ---------- Address {idx}/{total} ----------")
                            log_to_file(f"[PARCEL AUTOMATION] ID: {addr_id}")
                            log_to_file(f"[PARCEL AUTOMATION] Address: {address}")
                            
                            self._root.after(0, lambda i=idx, t=total, a=address: automation_status.config(
                                text=f"Processing {i}/{t}: {a[:40]}..."))
                            
                            try:
                                # Find and fill the search input
                                log_to_file("[PARCEL AUTOMATION] Looking for searchInput element...")
                                search_input = WebDriverWait(driver, 10).until(
                                    EC.presence_of_element_located((By.ID, "searchInput"))
                                )
                                log_to_file("[PARCEL AUTOMATION] searchInput element found")
                                
                                log_to_file("[PARCEL AUTOMATION] Clearing previous search...")
                                search_input.clear()
                                
                                log_to_file(f"[PARCEL AUTOMATION] Entering address: {address}")
                                search_input.send_keys(address)
                                
                                log_to_file("[PARCEL AUTOMATION] Pressing Enter...")
                                search_input.send_keys(Keys.RETURN)
                                
                                # Wait 10 seconds for results with visible countdown timer
                                wait_secs = 10
                                log_to_file(f"[PARCEL AUTOMATION] Waiting {wait_secs} seconds for results...")
                                for remaining in range(wait_secs, 0, -1):
                                    # Update status label with countdown each second
                                    def _update_status(msg=f"Processing {idx}/{total}: {address[:40]}... • waiting {remaining}s"):
                                        try:
                                            automation_status.config(text=msg)
                                        except Exception:
                                            pass
                                    self._root.after(0, _update_status)
                                    time.sleep(1)
                                    if not state.get('automation_running'):
                                        log_to_file("[PARCEL AUTOMATION] Wait aborted: automation stopped")
                                        break

                                # Check for site alert dialogs and handle gracefully
                                try:
                                    alert = driver.switch_to.alert
                                    try:
                                        alert_text = alert.text
                                    except Exception:
                                        alert_text = "<no text>"
                                    log_to_file(f"[PARCEL AUTOMATION] Alert present: {alert_text}")
                                    try:
                                        alert.accept()
                                    except Exception:
                                        try:
                                            alert.dismiss()
                                        except Exception:
                                            pass
                                    # Record as error for this address and continue
                                    results.append({
                                        'id': addr_id,
                                        'address': address,
                                        'error': f"Alert Text: {alert_text}"
                                    })
                                    log_to_file("[PARCEL AUTOMATION] Alert handled; moving to next address")
                                    continue
                                except NoAlertPresentException:
                                    pass
                                except UnexpectedAlertPresentException as ue:
                                    log_to_file(f"[PARCEL AUTOMATION] Unexpected alert: {ue}")
                                    # Best-effort handle
                                    try:
                                        alert = driver.switch_to.alert
                                        alert_text = alert.text
                                        alert.accept()
                                    except Exception:
                                        alert_text = str(ue)
                                    results.append({
                                        'id': addr_id,
                                        'address': address,
                                        'error': f"Alert Text: {alert_text}"
                                    })
                                    continue
                                
                                # Take screenshot
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                screenshot_filename = f"parcel_{metro_name}_{addr_id}_{timestamp}.png"
                                screenshot_path = output_dir / screenshot_filename
                                
                                log_to_file(f"[PARCEL AUTOMATION] Taking screenshot: {screenshot_filename}")
                                driver.save_screenshot(str(screenshot_path))
                                log_to_file(f"[PARCEL AUTOMATION] Screenshot saved: {screenshot_path}")
                                
                                # Extract text from screenshot using OCR
                                try:
                                    log_to_file("[PARCEL AUTOMATION] Starting OCR extraction...")
                                    img = Image.open(screenshot_path)
                                    log_to_file(f"[PARCEL AUTOMATION] Image loaded: {img.size[0]}x{img.size[1]} pixels")
                                    
                                    # Convert to opencv format
                                    img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
                                    log_to_file("[PARCEL AUTOMATION] Image converted to OpenCV format")
                                    
                                    # Preprocess for better OCR
                                    gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
                                    log_to_file("[PARCEL AUTOMATION] Image converted to grayscale")
                                    
                                    log_to_file("[PARCEL AUTOMATION] Running Tesseract OCR...")
                                    text = pytesseract.image_to_string(gray)
                                    log_to_file(f"[PARCEL AUTOMATION] OCR extracted {len(text)} characters")
                                    log_to_file(f"[PARCEL AUTOMATION] OCR preview (first 200 chars): {text[:200]}")
                                    
                                    # Try to extract structured data
                                    log_to_file("[PARCEL AUTOMATION] Extracting structured fields...")
                                    fields = extract_parcel_fields(text)
                                    log_to_file(f"[PARCEL AUTOMATION] Extracted {len(fields)} fields: {list(fields.keys())}")
                                    
                                    extracted = {
                                        'id': addr_id,
                                        'address': address,
                                        'screenshot': str(screenshot_path),
                                        'timestamp': timestamp,
                                        'metro': metro_name,
                                        'ocr_text': text,
                                        'fields': fields
                                    }
                                    results.append(extracted)
                                    log_to_file(f"[PARCEL AUTOMATION] Address data extracted and added to batch results")
                                    
                                except Exception as ocr_err:
                                    log_to_file(f"[PARCEL AUTOMATION] OCR ERROR for {address}: {ocr_err}")
                                    log_exception("[PARCEL AUTOMATION OCR]")
                                    results.append({
                                        'id': addr_id,
                                        'address': address,
                                        'screenshot': str(screenshot_path),
                                        'error': str(ocr_err)
                                    })
                                
                            except Exception as addr_err:
                                log_to_file(f"[PARCEL AUTOMATION] ADDRESS PROCESSING ERROR for {address}: {addr_err}")
                                log_exception("[PARCEL AUTOMATION ADDRESS]")
                                results.append({
                                    'id': addr_id,
                                    'address': address,
                                    'error': str(addr_err)
                                })
                        
                        # Save combined results
                        log_to_file(f"[PARCEL AUTOMATION] Processing complete. Processed {len(results)} addresses")
                        if results:
                            combined_filename = f"parcel_batch_{metro_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                            combined_path = output_dir / combined_filename
                            log_to_file(f"[PARCEL AUTOMATION] Saving batch results: {combined_filename}")
                            with open(combined_path, 'w', encoding='utf-8') as cf:
                                json.dump(results, cf, indent=2, ensure_ascii=False)
                            log_to_file(f"[PARCEL AUTOMATION] Batch results saved: {combined_path}")
                            
                            # Log summary
                            successful = len([r for r in results if 'error' not in r])
                            failed = len([r for r in results if 'error' in r])
                            log_to_file(f"[PARCEL AUTOMATION] SUMMARY: {successful} successful, {failed} failed")
                        
                        self._root.after(0, lambda: automation_status.config(
                            text=f"✓ Completed {len(results)}/{total} addresses"))
                        log_to_file(f"[PARCEL AUTOMATION] ========== AUTOMATION COMPLETED ==========")
                        
                    except Exception as auto_err:
                        log_to_file(f"[PARCEL AUTOMATION] CRITICAL ERROR: {auto_err}")
                        log_exception("[PARCEL AUTOMATION CRITICAL]")
                        self._root.after(0, lambda: automation_status.config(text=f"Error: {str(auto_err)[:50]}"))
                    finally:
                        if driver:
                            try:
                                log_to_file("[PARCEL AUTOMATION] Closing Chrome WebDriver...")
                                driver.quit()
                                log_to_file("[PARCEL AUTOMATION] Chrome WebDriver closed")
                            except Exception as quit_err:
                                log_to_file(f"[PARCEL AUTOMATION] Error closing WebDriver: {quit_err}")
                        state['automation_running'] = False
                        self._root.after(0, lambda: start_btn.config(state="normal", text="▶ Start Parcel Capture"))
                        log_to_file("[PARCEL AUTOMATION] Automation state reset to stopped")
                
                def start_automation():
                    if not state.get('automation_running'):
                        log_to_file("[PARCEL AUTOMATION] Start button clicked - launching automation thread")
                        threading.Thread(target=run_parcel_automation, daemon=True).start()
                    else:
                        log_to_file("[PARCEL AUTOMATION] Start button clicked but automation already running")
                        threading.Thread(target=run_parcel_automation, daemon=True).start()
                
                start_btn.config(command=start_automation)

                def fetch_and_fill():
                    import requests
                    try:
                        from urllib.parse import quote
                        url = php_url(f"step5/get_empty_parcels_list.php?metro={quote(metro_name)}&limit={state['limit']}&page={state['page']}")
                        log_to_file(f"[EMPTY PARCELS WINDOW] Fetching empty addresses for metro: {metro_name}")
                        log_to_file(f"[EMPTY PARCELS WINDOW] API URL: {url}")
                        log_to_file(f"[EMPTY PARCELS WINDOW] Page: {state['page']}, Limit: {state['limit']}")
                        
                        r = requests.get(url, timeout=30)
                        log_to_file(f"[EMPTY PARCELS WINDOW] Response status: {r.status_code}")
                        r.raise_for_status()
                        
                        data = r.json()
                        log_to_file(f"[EMPTY PARCELS WINDOW] Response keys: {list(data.keys())}")
                        
                        rows = data.get('rows') or data.get('data') or []
                        log_to_file(f"[EMPTY PARCELS WINDOW] Received {len(rows)} rows")
                        if rows:
                            log_to_file(f"[EMPTY PARCELS WINDOW] First row: ID={rows[0].get('id')}, Address={rows[0].get('formatted_address','')[:50]}")
                        
                        has_next = bool(data.get('has_next')) if isinstance(data, dict) else (len(rows) >= state['limit'])
                        log_to_file(f"[EMPTY PARCELS WINDOW] Has next page: {has_next}")

                        def fill_ui():
                            try:
                                log_to_file(f"[EMPTY PARCELS WINDOW] Filling UI with {len(rows)} rows")
                                state['last_url'] = url
                                # Clear existing
                                for item in tree.get_children():
                                    tree.delete(item)
                                for row in rows:
                                    tree.insert("", "end", values=(
                                        row.get('id'),
                                        row.get('formatted_address') or ''
                                    ))
                                status.config(text=f"Loaded {len(rows)} address(es)")
                                page_lbl.config(text=f"Page {state['page']}")
                                # Enable/disable buttons
                                btn_prev.config(state=("normal" if state['page'] > 1 else "disabled"))
                                state['has_next'] = has_next
                                btn_next.config(state=("normal" if state['has_next'] else "disabled"))
                                try:
                                    url_label.config(text=state['last_url'])
                                except Exception:
                                    pass
                                log_to_file(f"[EMPTY PARCELS WINDOW] UI updated successfully")
                            except Exception as _fill_err:
                                log_to_file(f"[EMPTY PARCELS WINDOW] UI FILL ERROR: {_fill_err}")
                                log_exception("[EMPTY PARCELS WINDOW UI]")
                                status.config(text=f"Failed to render: {_fill_err}")
                        self._root.after(0, fill_ui)
                    except Exception as _req_err:
                        log_to_file(f"[EMPTY PARCELS WINDOW] REQUEST ERROR: {_req_err}")
                        log_exception("[EMPTY PARCELS WINDOW REQUEST]")
                        self._root.after(0, lambda: status.config(text=f"Request failed: {_req_err}"))

                def go_prev():
                    if state['page'] > 1:
                        log_to_file(f"[EMPTY PARCELS WINDOW] Previous page clicked: {state['page']} -> {state['page']-1}")
                        state['page'] -= 1
                        status.config(text="Loading…")
                        threading.Thread(target=fetch_and_fill, daemon=True).start()

                def go_next():
                    if state.get('has_next'):
                        log_to_file(f"[EMPTY PARCELS WINDOW] Next page clicked: {state['page']} -> {state['page']+1}")
                        state['page'] += 1
                        status.config(text="Loading…")
                        threading.Thread(target=fetch_and_fill, daemon=True).start()

                btn_prev.config(command=go_prev)
                btn_next.config(command=go_next)

                # Double-click to open Google Maps for the address
                def on_dbl(_e):
                    try:
                        item = tree.identify_row(_e.y)
                        if not item:
                            return
                        vals = tree.item(item, 'values') or []
                        addr = str(vals[1] or '').strip()
                        if addr:
                            log_to_file(f"[EMPTY PARCELS WINDOW] Double-clicked address: {addr}")
                            from urllib.parse import quote
                            maps_url = f"https://www.google.com/maps/search/?api=1&query={quote(addr)}"
                            log_to_file(f"[EMPTY PARCELS WINDOW] Opening Google Maps: {maps_url}")
                            launch_manual_browser(maps_url)
                    except Exception as dbl_err:
                        log_to_file(f"[EMPTY PARCELS WINDOW] Double-click error: {dbl_err}")
                tree.bind("<Double-1>", on_dbl)

                log_to_file(f"[EMPTY PARCELS WINDOW] Starting initial data fetch...")
                threading.Thread(target=fetch_and_fill, daemon=True).start()
            except Exception as _win_err:
                log_to_file(f"[EMPTY PARCELS WINDOW] WINDOW CREATION ERROR: {_win_err}")
                log_exception("[EMPTY PARCELS WINDOW]")

        # expose for calls above
        self._show_empty_parcels_window = _show_empty_parcels_window
        
        # Loading indicator overlay (initially hidden)
        self._loading_overlay = tk.Label(tree_frame, text="⏳ Loading...", fg="#FFFFFF", bg="#2C3E50", 
                                         font=("Segoe UI", 12, "bold"), bd=2, relief="raised", padx=20, pady=10)
        # Don't pack it yet - we'll place() it when needed
        self._loading_table_name = ""  # Track which table is loading
        
    # Bottom status bar
        queue_status_bar = tk.Frame(self._queue_frame, bg=chip_bg)
        queue_status_bar.pack(fill="x", padx=4, pady=(0, 4))
        self._queue_status_label = tk.Label(queue_status_bar, text="Click a status chip or button to load data", fg=muted, bg=chip_bg, font=("Consolas", 8))
        self._queue_status_label.pack(side="left")
        
        # Auto Run checkbox
        self._auto_run_enabled = tk.BooleanVar(value=False)  # Default: manual mode
        auto_run_check = tk.Checkbutton(
            queue_status_bar, 
            text="Auto Run", 
            variable=self._auto_run_enabled,
            fg=fg, 
            bg=chip_bg, 
            selectcolor=chip_bg,
            activebackground=chip_bg,
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        auto_run_check.pack(side="right", padx=(8, 4))
        
        # Auto-refresh toggle
        auto_refresh_lbl = tk.Label(queue_status_bar, text="Auto Refresh (5s)", fg=ok, bg=chip_bg, font=("Segoe UI", 8, "bold"), padx=4, pady=1, cursor="hand2")
        auto_refresh_lbl.pack(side="right", padx=4)
        self._auto_refresh_enabled = True
        
        def toggle_auto_refresh(_e):
            self._auto_refresh_enabled = not self._auto_refresh_enabled
            auto_refresh_lbl.config(fg=ok if self._auto_refresh_enabled else muted)
        auto_refresh_lbl.bind("<Button-1>", toggle_auto_refresh)
        
        # Create Entry button
        create_entry_btn = tk.Label(queue_status_bar, text="➕ Create Entry", fg="#2ECC71", bg=chip_bg, font=("Segoe UI", 8, "bold"), padx=4, pady=1, cursor="hand2")
        create_entry_btn.pack(side="right", padx=4)
        
        def create_new_entry(_e):
            try:
                current_table = self._current_table.get()
                log_to_file(f"[Queue] Create Entry clicked, current table: {current_table}")
                self._show_edit_dialog(None, current_table)
            except Exception as create_err:
                log_to_file(f"[Queue] Create Entry error: {create_err}")
                log_exception("Create Entry")
        create_entry_btn.bind("<Button-1>", create_new_entry)
        
        # Metro selector initialization (widget already created in header)
        try:
            # Require metros to load before first table refresh
            self._require_metros_first = True
            self._metros_loaded = False
            # Initialize with a safe default so it never looks empty
            try:
                self._metro_combo['values'] = ["All"]
                self._selected_metro.set("All")  # Explicitly set to All
            except Exception as _init_combo_err:
                log_to_file(f"[Metro] Failed to set initial values: {_init_combo_err}")

            # Loader helpers for metro fetch
            def _metro_loading_start():
                try:
                    self._metro_combo.configure(state="disabled")
                except Exception:
                    pass
                try:
                    if getattr(self, "_metro_pb", None):
                        # Ensure visible and animate
                        self._metro_pb.pack(side="left", padx=(6, 0))
                        self._metro_pb.start(10)
                except Exception:
                    pass

            def _metro_loading_stop():
                try:
                    self._metro_combo.configure(state="readonly")
                except Exception:
                    pass
                try:
                    if getattr(self, "_metro_pb", None):
                        self._metro_pb.stop()
                        self._metro_pb.pack_forget()
                except Exception:
                    pass

            def on_metro_change(_e=None):
                try:
                    current_table = self._current_table.get()
                    # Read directly from combobox widget, not StringVar
                    selected_metro = self._metro_combo.get().strip()
                    log_to_file(f"[Metro] Metro changed to: '{selected_metro}' | Current table: {current_table}")
                    # Update the StringVar to match
                    self._selected_metro.set(selected_metro)
                    
                    # Refresh table for any tab when metro changes
                    def _do_refresh():
                        try:
                            if str(current_table).lower() == 'parcel' and hasattr(self, '_trigger_parcel_refresh'):
                                self._trigger_parcel_refresh()
                            else:
                                self._refresh_queue_table(silent=False)
                        except Exception as _rerr:
                            log_to_file(f"[Metro] Refresh on change failed: {_rerr}")
                    # Debounce slightly to ensure combobox value has settled
                    try:
                        self._root.after(100, _do_refresh)
                    except Exception:
                        _do_refresh()
                except Exception as _e:
                    log_to_file(f"[Metro] Error in on_metro_change: {_e}")
            self._metro_combo.bind("<<ComboboxSelected>>", on_metro_change)

            def _load_metros_list_async():
                try:
                    import requests
                    # Load distinct metro names via local API
                    values_api = []
                    try:
                        api_url = php_url("step5/get_major_metros.php?only=names")
                        log_to_file(f"[Metro] Fetching from: {api_url}")
                        r = requests.get(api_url, timeout=15)  # Increased timeout
                        log_to_file(f"[Metro] Got response: status={r.status_code}")
                        if r.status_code == 200:
                            data = r.json()
                            names = []
                            if isinstance(data, dict):
                                if isinstance(data.get('names'), list):
                                    names = [str(x).strip() for x in data.get('names') if x]
                                elif isinstance(data.get('rows'), list):
                                    for m in data['rows']:
                                        if isinstance(m, dict):
                                            nm = m.get('metro_name')
                                            if nm:
                                                names.append(str(nm).strip())
                            # Deduplicate and sort
                            names = sorted(list(dict.fromkeys([n for n in names if n])))
                            values_api = names
                            log_to_file(f"[Metro] API returned {len(names)} metros: {names}")
                    except Exception as _api_err:
                        log_to_file(f"[Metro] API load failed: {_api_err}")

                    if not values_api:
                        log_to_file("[Metro] No API metros returned; using All only")

                    def _apply_values():
                        try:
                            # Stop metro loader and re-enable combobox
                            try:
                                _metro_loading_stop()
                            except Exception:
                                pass
                            # Filter out any blank/empty values from API response
                            filtered_api = [str(v).strip() for v in values_api if v and str(v).strip()] if values_api else []
                            # Don't include "All" option
                            values = filtered_api
                            self._metro_combo['values'] = values
                            # Ensure current selection is valid, default to Seattle if not
                            current = self._selected_metro.get()
                            if current not in values:
                                self._selected_metro.set("Seattle" if "Seattle" in values else (values[0] if values else "Seattle"))
                            # Mark metros ready so table loads can proceed
                            try:
                                self._metros_loaded = True
                            except Exception:
                                pass
                            log_to_file(f"[Metro] Applied metros: {len(values)} options - {values}")
                        except Exception as _ap_err:
                            log_to_file(f"[Metro] Failed to apply metros: {_ap_err}")

                    try:
                        self._root.after(0, _apply_values)
                    except Exception as _sched_err:
                        log_to_file(f"[Metro] Scheduling apply failed, applying directly: {_sched_err}")
                        try:
                            _apply_values()
                        except Exception:
                            pass
                except Exception as _apply_err:
                    log_to_file(f"[Metro] Apply failed: {_apply_err}")

            # Delay thread start until after mainloop begins
            try:
                # Start loader now
                try:
                    _metro_loading_start()
                except Exception:
                    pass
                def _start_metro_thread():
                    try:
                        threading.Thread(target=_load_metros_list_async, daemon=True).start()
                        log_to_file("[Metro] Thread started after mainloop initialization")
                    except Exception as _th_err:
                        log_to_file(f"[Metro] Thread start failed: {_th_err}")
                # Schedule thread start immediately after mainloop enters
                self._root.after(0, _start_metro_thread)
            except Exception as _sched_err:
                log_to_file(f"[Metro] Failed to schedule thread start: {_sched_err}")
            # Always visible – do not hide per tab
        except Exception as _ui_err:
            log_to_file(f"[Metro] UI setup failed: {_ui_err}")
        
        # Helper functions for loading indicator
        def _show_loading():
            try:
                # Update text to show which table is loading
                table_name = self._loading_table_name or "data"
                self._loading_overlay.config(text=f"⏳ Loading {table_name}...")
                # Center the loading overlay on the tree_frame
                tree_frame.update_idletasks()
                x = tree_frame.winfo_width() // 2 - 100
                y = tree_frame.winfo_height() // 2 - 20
                self._loading_overlay.place(x=x, y=y)
                self._loading_overlay.lift()
            except Exception as e:
                log_to_file(f"[Queue] Failed to show loading: {e}")
        
        def _hide_loading():
            try:
                self._loading_overlay.place_forget()
                # Stop ETA ticker if running
                try:
                    if getattr(self, '_loading_eta_job', None) is not None:
                        self._root.after_cancel(self._loading_eta_job)
                        self._loading_eta_job = None
                except Exception:
                    pass
            except Exception as e:
                log_to_file(f"[Queue] Failed to hide loading: {e}")
        
        self._show_loading = _show_loading
        self._hide_loading = _hide_loading

        # ETA ticker support for loader overlay
        self._loading_eta_seconds = 0
        self._loading_eta_job = None
        def _start_eta(seconds: int):
            try:
                self._loading_eta_seconds = max(0, int(seconds))
                def _tick():
                    try:
                        table_name = self._loading_table_name or "data"
                        eta_txt = f"⏳ Loading {table_name}… (~{self._loading_eta_seconds}s)"
                        self._loading_overlay.config(text=eta_txt)
                        if self._loading_eta_seconds > 0:
                            self._loading_eta_seconds -= 1
                            self._loading_eta_job = self._root.after(1000, _tick)
                        else:
                            self._loading_overlay.config(text=f"⏳ Loading {table_name}…")
                            self._loading_eta_job = None
                    except Exception as _et:
                        log_to_file(f"[Queue] ETA tick failed: {_et}")
                # Kick off ticker
                self._loading_eta_job = self._root.after(0, _tick)
            except Exception as _es:
                log_to_file(f"[Queue] ETA start failed: {_es}")
        self._start_eta = _start_eta
        
        # Helper to trigger parcel refresh with loader
        def _trigger_parcel_refresh():
            try:
                self._loading_table_name = "Parcel"
                if hasattr(self, '_show_loading'):
                    self._show_loading()
                self._refresh_queue_table(silent=False)
            except Exception as e:
                log_to_file(f"[Parcel] Refresh trigger failed: {e}")
        self._trigger_parcel_refresh = _trigger_parcel_refresh
        
        # Define _refresh_queue_table function
        def _refresh_queue_table(silent: bool = False):
            log_to_file(f"[Queue] _refresh_queue_table() called, silent={silent}")
            # Prevent multiple simultaneous refreshes
            if hasattr(self, '_refresh_in_progress') and self._refresh_in_progress:
                log_to_file("[Queue] Refresh already in progress, skipping...")
                return
            log_to_file(f"[Queue] Setting _refresh_in_progress=True")
            self._refresh_in_progress = True
            # If metros must load first, defer until loaded
            try:
                if getattr(self, '_require_metros_first', False) and not getattr(self, '_metros_loaded', True):
                    if not silent and hasattr(self, '_root'):
                        try:
                            self._root.after(0, lambda: self._queue_status_label.config(text="Loading metros (~10s)..."))
                        except Exception:
                            pass
                    # Ensure metro loader visible
                    try:
                        if getattr(self, '_metro_pb', None):
                            self._metro_pb.pack(side="left", padx=(6, 0))
                            self._metro_pb.start(10)
                    except Exception:
                        pass
                    # Retry shortly
                    try:
                        self._root.after(250, lambda: self._refresh_queue_table(silent))
                    except Exception:
                        pass
                    return
            except Exception:
                pass
            
            # Capture values on main thread before starting background thread
            try:
                current_table = self._current_table.get()
                current_status = self._current_status.get()
                try:
                    account_search = (self._accounts_search_var.get().strip() if hasattr(self, '_accounts_search_var') else "")
                except Exception:
                    account_search = ""
                try:
                    # Read metro from combobox widget directly for more reliable capture
                    selected_metro = (self._metro_combo.get().strip() if hasattr(self, '_metro_combo') else "All")
                    if not selected_metro:
                        selected_metro = "All"
                    # Debug: log what we captured
                    if str(current_table).lower() == 'parcel':
                        log_to_file(f"[Queue] Captured metro value: '{selected_metro}' (type: {type(selected_metro).__name__})")
                except Exception as e:
                    log_to_file(f"[Queue] Failed to get metro: {e}")
                    selected_metro = "All"
            except Exception as e:
                log_to_file(f"[Queue] Error getting table/status values: {e}")
                return
            
            try:
                eta_sec = 8
                if str(current_table).lower() == 'parcel':
                    eta_sec = 10 if (selected_metro and selected_metro != 'All') else 15
                if hasattr(self, '_start_eta'):
                    self._start_eta(eta_sec)
            except Exception:
                pass
            
            # Show loading indicator
            if not silent and hasattr(self, '_show_loading'):
                self._root.after(0, self._show_loading)
            # Update status immediately on main thread (only for manual refresh)
            if not silent and hasattr(self, '_root'):
                self._root.after(0, lambda: self._queue_status_label.config(text="Loading..."))
            
            if not silent:
                log_to_file("[Queue] Background fetch started")
            
            if str(current_table).lower() == 'parcel':
                # Parcel tab: load google_addresses where king_county_parcels_id is NULL
                try:
                    import mysql.connector
                    if not silent:
                        log_to_file(f"[Parcel] Loading from google_addresses where king_county_parcels_id IS NULL...")
                    
                    conn = mysql.connector.connect(
                        host='localhost',
                        port=3306,
                        user='root',
                        password='',
                        database='offta',
                        connect_timeout=10
                    )
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT id, place_id, building_name, 
                               JSON_UNQUOTE(JSON_EXTRACT(json_dump, '$.formatted_address')) as formatted_address
                        FROM google_addresses 
                        WHERE king_county_parcels_id IS NULL 
                        ORDER BY id DESC 
                        LIMIT 500
                    """)
                    addresses = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    
                    rows = []
                    for addr in addresses:
                        rows.append({
                            'id': addr.get('id'),
                            'link': addr.get('formatted_address') or addr.get('place_id') or '',
                            'name': addr.get('building_name') or '',
                            'run_interval_minutes': 0,
                            'next_run': None,
                            'processed_at': None,
                            'status': 'queued',
                            'steps': {}
                        })
                    custom_source = 'parcel'
                    if not silent:
                        log_to_file(f"[Parcel] ✓ Loaded {len(rows)} addresses without parcel IDs")
                except Exception as e:
                    error_occurred = True
                    error_msg = f"Parcel load failed: {str(e)[:80]}"
                    log_to_file(f"[Parcel] {error_msg}")
                    rows = []
            elif str(current_table).lower() == 'queue_websites':
                # Networks tab: load from queue_websites database table in BACKGROUND thread
                queue_tree = self._queue_tree  # Capture tree reference for background thread
                status_filter = current_status if current_status and current_status.lower() != 'all' else None
                
                def _bg_load():
                    import mysql.connector
                    from datetime import date
                    
                    # Configure Networks columns FIRST (on main thread)
                    def _configure_columns():
                        try:
                            self._set_queue_columns_for_table("queue_websites")
                            log_to_file(f"[Networks] BG: Configured columns for Networks tab")
                        except Exception as col_err:
                            log_to_file(f"[Networks] BG: Column config error: {col_err}")
                    self._root.after(0, _configure_columns)
                    
                    try:
                        log_to_file(f"[Networks] BG: Loading from queue_websites table with stats (filter={status_filter})")
                        
                        DB_CONFIG = {
                            'host': 'localhost',
                            'port': 3306,
                            'user': 'root',
                            'password': '',
                            'database': 'offta'
                        }
                        
                        conn = mysql.connector.connect(**DB_CONFIG, connect_timeout=3)
                        cursor = conn.cursor(dictionary=True)
                        
                        # Get selected date from dropdown (default to today)
                        try:
                            selected_date = self._selected_date.get()
                        except:
                            selected_date = date.today().strftime("%Y-%m-%d")
                        
                        # Get selected metro for filtering
                        try:
                            selected_metro = self._metro_combo.get().strip()
                        except:
                            selected_metro = "Seattle"
                        if not selected_metro:
                            selected_metro = "Seattle"
                        
                        # Join queue_websites with network_daily_stats to get SELECTED DATE's stats
                        # Join with major_metros to get metro_name and filter by selected metro
                        query = """
                            SELECT 
                                qw.*,
                                n.major_metro_id,
                                mm.metro_name,
                                nds.price_changes,
                                nds.apartments_added,
                                nds.apartments_subtracted,
                                nds.total_listings
                            FROM queue_websites qw
                            LEFT JOIN networks n ON qw.source_table = 'networks' AND qw.source_id = n.id
                            LEFT JOIN major_metros mm ON n.major_metro_id = mm.id
                            LEFT JOIN network_daily_stats nds ON qw.id = nds.network_id 
                                AND nds.date = %s
                            WHERE qw.source_table != 'king_county_parcels'
                            AND mm.metro_name = %s
                        """
                        params = [selected_date, selected_metro]
                        
                        # Add status filter if specified
                        if status_filter:
                            query += " AND qw.status = %s"
                            params.append(status_filter)
                        
                        query += " ORDER BY qw.processed_at DESC LIMIT 100"
                        
                        cursor.execute(query, params)
                        db_rows = cursor.fetchall()
                        cursor.close()
                        conn.close()
                        
                        bg_rows = []
                        status_counts = {'all': 0, 'queued': 0, 'running': 0, 'done': 0, 'error': 0}
                        
                        for row in db_rows:
                            status = (row.get('status') or 'queued').lower()
                            status_counts['all'] += 1
                            if status in status_counts:
                                status_counts[status] += 1
                            
                            # Get metro_name directly from JOIN
                            metro_name = row.get('metro_name') or ''
                            
                            bg_rows.append({
                                'id': row.get('id'),
                                'link': row.get('link') or '',
                                'name': row.get('name') or '',
                                'metro_name': metro_name,
                                'run_interval_minutes': row.get('run_interval_minutes') or 0,
                                'next_run': row.get('next_run'),
                                'processed_at': row.get('processed_at'),
                                'status': status,
                                'error_message': row.get('error_message') or '',
                                'price_changes': row.get('price_changes'),
                                'apartments_added': row.get('apartments_added'),
                                'apartments_subtracted': row.get('apartments_subtracted'),
                                'total_listings': row.get('total_listings'),
                                'steps': {}
                            })
                        log_to_file(f"[Networks] BG: Loaded {len(bg_rows)} networks, counts: {status_counts}")
                        
                        # Update UI on main thread
                        def _fill_tree():
                            try:
                                log_to_file(f"[Networks] UI: Clearing tree")
                                for item in queue_tree.get_children():
                                    queue_tree.delete(item)
                                
                                # Check tree column configuration
                                try:
                                    col_count = len(queue_tree["columns"])
                                    log_to_file(f"[Networks] UI: Tree has {col_count} columns: {queue_tree['columns']}")
                                except Exception as col_check_err:
                                    log_to_file(f"[Networks] UI: Could not check columns: {col_check_err}")
                                
                                log_to_file(f"[Networks] UI: Inserting {len(bg_rows)} rows")
                                for idx, row in enumerate(bg_rows):
                                    status = row.get('status', 'queued')
                                    
                                    # Status-based color coding
                                    if status == 'done':
                                        tag = 'done_row'
                                    elif status == 'error':
                                        tag = 'error_row'
                                    elif status == 'running':
                                        tag = 'running_row'
                                    else:  # queued
                                        tag = "even" if idx % 2 == 0 else "odd"
                                    
                                    # Format datetime
                                    last_run = row.get('processed_at', '')
                                    if last_run and hasattr(last_run, 'strftime'):
                                        last_run = last_run.strftime('%m/%d %H:%M')
                                    elif last_run:
                                        last_run = str(last_run)[:16]
                                    
                                    # Calculate minutes until next update: (Last + Int) - Now
                                    next_run_minutes = ''
                                    processed_at = row.get('processed_at')
                                    interval = row.get('run_interval_minutes', 0)
                                    if processed_at and interval:
                                        try:
                                            from datetime import datetime, timedelta
                                            if isinstance(processed_at, str):
                                                processed_at = datetime.strptime(processed_at, '%Y-%m-%d %H:%M:%S')
                                            next_update_time = processed_at + timedelta(minutes=int(interval))
                                            now = datetime.now()
                                            minutes_until = int((next_update_time - now).total_seconds() / 60)
                                            
                                            # Convert to days, hours and minutes
                                            abs_minutes = abs(minutes_until)
                                            days = abs_minutes // (60 * 24)
                                            remaining_minutes = abs_minutes % (60 * 24)
                                            hours = remaining_minutes // 60
                                            mins = remaining_minutes % 60
                                            
                                            if minutes_until < 0:
                                                # Past due
                                                if days > 0:
                                                    next_run_minutes = f"{days}d {hours}h ago"
                                                elif hours > 0:
                                                    next_run_minutes = f"{hours}h {mins}m ago"
                                                else:
                                                    next_run_minutes = f"{mins}m ago"
                                            else:
                                                # Future
                                                if days > 0:
                                                    next_run_minutes = f"{days}d {hours}h"
                                                elif hours > 0:
                                                    next_run_minutes = f"{hours}h {mins}m"
                                                else:
                                                    next_run_minutes = f"{mins}m"
                                        except Exception:
                                            next_run_minutes = '-'
                                    next_run = next_run_minutes if next_run_minutes else '-'
                                    
                                    # Format stats - show "-" instead of 0 or None
                                    price_changes = row.get('price_changes')
                                    apartments_added = row.get('apartments_added')
                                    apartments_subtracted = row.get('apartments_subtracted')
                                    total_listings = row.get('total_listings')
                                    
                                    price_changes_str = str(price_changes) if price_changes else '-'
                                    apartments_added_str = str(apartments_added) if apartments_added else '-'
                                    apartments_subtracted_str = str(apartments_subtracted) if apartments_subtracted else '-'
                                    total_listings_str = str(total_listings) if total_listings else '-'
                                    
                                    # Add play button to ID column
                                    id_with_play = f"▶ {row.get('id', '')}"
                                    
                                    # Networks: Must provide 14 values to match tree column count
                                    # Tree columns: ID, Link, Metro, Int, Last, Next, Status, Δ$, +, -, Total, ✏️, hidden1, hidden2
                                    values_tuple = (
                                        id_with_play,                    # ID
                                        row.get('link', ''),             # Link
                                        "",                              # Metro (hidden for Networks)
                                        row.get('run_interval_minutes', 0), # Int
                                        last_run,                        # Last
                                        next_run,                        # Next
                                        status,                          # Status
                                        price_changes_str,               # Δ$
                                        apartments_added_str,            # +
                                        apartments_subtracted_str,       # -
                                        total_listings_str,              # Total
                                        "✏️",                           # Edit button
                                        "",                              # hidden1
                                        ""                               # hidden2
                                    )
                                    if idx < 2:  # Log first 2 rows
                                        log_to_file(f"[Networks] BG: Inserting row {idx}: {len(values_tuple)} values")
                                    item_id = queue_tree.insert("", "end", values=values_tuple, tags=(tag,))
                                    
                                    # Store error tooltip for Networks status column (#6)
                                    error_msg = row.get('error_message', '')
                                    if error_msg and hasattr(self, '_cell_tooltips'):
                                        self._cell_tooltips[(item_id, '#6')] = error_msg
                                
                                # Update status button counts
                                if hasattr(self, '_status_buttons'):
                                    for status_key, count_val in status_counts.items():
                                        if status_key in self._status_buttons:
                                            btn = self._status_buttons[status_key]
                                            btn.config(text=f"{status_key.capitalize()} ({count_val})")
                                
                                log_to_file(f"[Networks] UI: ✓ Tree populated with {len(bg_rows)} rows")
                            except Exception as ui_err:
                                log_to_file(f"[Networks] UI ERROR: {ui_err}")
                                import traceback
                                traceback.print_exc()
                            finally:
                                if hasattr(self, '_hide_loading'):
                                    self._hide_loading()
                                self._refresh_in_progress = False
                        
                        self._root.after(0, _fill_tree)
                        
                    except Exception as e:
                        log_to_file(f"[Networks] BG ERROR: {str(e)[:80]}")
                        import traceback
                        traceback.print_exc()
                        def _show_error():
                            if hasattr(self, '_hide_loading'):
                                self._hide_loading()
                            self._refresh_in_progress = False
                        self._root.after(0, _show_error)
                
                # Start background thread and RETURN immediately
                threading.Thread(target=_bg_load, daemon=True).start()
                return  # EXIT EARLY - don't process the rows variable below
            elif str(current_table).lower() in ('listing_websites', 'websites'):
                # Websites tab: load from google_places where Website is not empty
                # Configure Websites columns FIRST
                try:
                    self._set_queue_columns_for_table("listing_websites")
                    log_to_file(f"[Websites] Configured columns for Websites tab")
                except Exception as col_err:
                    log_to_file(f"[Websites] Column config error: {col_err}")
                
                try:
                    import mysql.connector
                    if not silent:
                        log_to_file(f"[Websites] Loading from google_places database...")
                    
                    conn = mysql.connector.connect(
                        host='localhost',
                        port=3306,
                        user='root',
                        password='',
                        database='offta',
                        connect_timeout=10
                    )
                    cursor = conn.cursor(dictionary=True)
                    
                    # Get selected metro name for filtering
                    selected_metro = (self._metro_combo.get().strip() if hasattr(self, '_metro_combo') else "Seattle")
                    if not selected_metro:
                        selected_metro = "Seattle"
                    
                    # Filter by metro name
                    cursor.execute("""
                        SELECT gp.id, gp.Website, gp.Name, gp.availability_website, mm.metro_name
                        FROM google_places gp
                        LEFT JOIN major_metros mm ON gp.major_metro_id = mm.id
                        WHERE gp.Website IS NOT NULL AND gp.Website != '' 
                        AND mm.metro_name = %s
                        ORDER BY 
                            CASE 
                                WHEN gp.availability_website LIKE '%http:%' OR gp.availability_website LIKE '%https:%' THEN 0 
                                ELSE 1 
                            END,
                            gp.id DESC 
                        LIMIT 200
                    """, (selected_metro,))
                    gps = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    
                    rows = []
                    for gp in gps:
                        rows.append({
                            'id': gp.get('id'),
                            'link': gp.get('Website') or '',
                            'name': gp.get('Name') or '',
                            'metro_name': gp.get('metro_name') or 'Seattle',
                            'availability_website': gp.get('availability_website') or '',
                            'run_interval_minutes': 0,
                            'next_run': None,
                            'processed_at': None,
                            'status': 'queued',
                            'steps': {}
                        })
                    custom_source = 'websites'
                    if not silent:
                        log_to_file(f"[Websites] ✓ Loaded {len(rows)} websites from database")
                except Exception as e:
                    error_occurred = True
                    error_msg = f"Websites load failed: {str(e)[:80]}"
                    log_to_file(f"[Websites] {error_msg}")
                    rows = []
            elif str(current_table).lower() == 'accounts':
                        # Special handling for Accounts tab: list accounts via API with optional search filter
                        try:
                            api_url = php_url("step5/get_accounts.php")
                            if account_search:
                                api_url += f"?search={requests.utils.quote(account_search)}"
                            
                            log_to_file(f"[Accounts] Calling API: {api_url}")
                            r = requests.get(api_url, timeout=10)
                            if r.status_code == 200:
                                data = r.json()
                                if isinstance(data, dict) and data.get('ok'):
                                    accs = data.get('accounts', [])
                                    rows = []
                                    for a in accs:
                                        full_name = (f"{a.get('first_name') or ''} {a.get('last_name') or ''}" ).strip()
                                        display_name = full_name if full_name else (a.get('username') or '')
                                        rows.append({
                                            'id': a.get('id'),
                                            'link': a.get('email') or '',
                                            'name': display_name,
                                            'role': a.get('role') or '',
                                            'registered': a.get('registered'),
                                            'last_seen': a.get('last_seen'),
                                            'run_interval_minutes': 0,
                                            'processed_at': None,
                                            'steps': {}
                                        })
                                    custom_source = 'accounts'
                                    if not silent:
                                        log_to_file(f"[Accounts] Loaded {len(rows)} accounts (search='{account_search}')")
                                else:
                                    error_occurred = True
                                    error_msg = f"Accounts API returned error: {data.get('error', 'unknown')}"
                                    log_to_file(f"[Accounts] {error_msg}")
                            else:
                                error_occurred = True
                                error_msg = f"Accounts API failed: HTTP {r.status_code}"
                                log_to_file(f"[Accounts] {error_msg}")
                        except Exception as api_err:
                            error_occurred = True
                            error_msg = f"Accounts load failed: {str(api_err)[:80]}"
                            log_to_file(f"[Accounts] {error_msg}")
            elif str(current_table).lower() == 'code':
                        # Code tab: show cities with code_website from cities table
                        try:
                            api_url = php_url("step5/get_code_cities.php?limit=500")
                            log_to_file(f"[Code] Calling API: {api_url}")
                            r = requests.get(api_url, timeout=10)
                            if r.status_code == 200:
                                data = r.json()
                                if isinstance(data, dict) and data.get('ok'):
                                    cities = data.get('rows', [])
                                    rows = []
                                    for c in cities:
                                        rows.append({
                                            'id': c.get('id'),
                                            'link': c.get('code_website') or '',
                                            'name': c.get('city_name') or '',
                                            'role': '',
                                            'registered': None,
                                            'last_seen': None,
                                            'run_interval_minutes': 0,
                                            'processed_at': None,
                                            'steps': {}
                                        })
                                    custom_source = 'code'
                                    if not silent:
                                        log_to_file(f"[Code] Loaded {len(rows)} cities with code_website")
                                else:
                                    error_occurred = True
                                    error_msg = f"Code API returned error: {data.get('error', 'unknown')}"
                                    log_to_file(f"[Code] {error_msg}")
                            else:
                                error_occurred = True
                                error_msg = f"Code API failed: HTTP {r.status_code}"
                                log_to_file(f"[Code] {error_msg}")
                        except Exception as api_err:
                            error_occurred = True
                            error_msg = f"Code load failed: {str(api_err)[:80]}"
                            log_to_file(f"[Code] {error_msg}")
            elif str(current_table).lower() == '911':
                        # 911 tab: show cities with 911_website from cities table
                        try:
                            api_url = php_url("step5/get_911_cities.php?limit=500")
                            log_to_file(f"[911] Calling API: {api_url}")
                            r = requests.get(api_url, timeout=10)
                            if r.status_code == 200:
                                data = r.json()
                                if isinstance(data, dict) and data.get('ok'):
                                    cities = data.get('rows', [])
                                    rows = []
                                    for c in cities:
                                        rows.append({
                                            'id': c.get('id'),
                                            'link': c.get('911_website') or '',
                                            'name': c.get('city_name') or '',
                                            'role': '',
                                            'registered': None,
                                            'last_seen': None,
                                            'run_interval_minutes': 0,
                                            'processed_at': None,
                                            'steps': {}
                                        })
                                    custom_source = '911'
                                    if not silent:
                                        log_to_file(f"[911] Loaded {len(rows)} cities with 911_website")
                                else:
                                    error_occurred = True
                                    error_msg = f"911 API returned error: {data.get('error', 'unknown')}"
                                    log_to_file(f"[911] {error_msg}")
                            else:
                                error_occurred = True
                                error_msg = f"911 API failed: HTTP {r.status_code}"
                                log_to_file(f"[911] {error_msg}")
                        except Exception as api_err:
                            error_occurred = True
                            error_msg = f"911 load failed: {str(api_err)[:80]}"
                            log_to_file(f"[911] {error_msg}")
            else:
                # COMMENTED OUT: Networks/Websites/Accounts/Code tabs - has indentation issues
                error_occurred = True
                error_msg = "This tab is temporarily disabled"
                log_to_file(f"[Queue] Tab {current_table}: {error_msg}")
                rows = []
            
            # POPULATE THE TREE WITH THE LOADED DATA
            try:
                if not silent:
                    log_to_file(f"[Queue] Populating tree with {len(rows)} rows")
                
                # Clear existing tree
                for item in self._queue_tree.get_children():
                    self._queue_tree.delete(item)
                
                # Insert rows into tree
                for idx, row in enumerate(rows):
                    row_id = row.get('id', '')
                    link = row.get('link', '')
                    run_interval = row.get('run_interval_minutes', 0)
                    next_run = row.get('next_run', '')
                    last_run = row.get('processed_at', '')
                    status = row.get('status', 'queued')
                    error_msg = row.get('error_message', '')
                    
                    # Format datetime fields
                    if last_run and hasattr(last_run, 'strftime'):
                        last_run = last_run.strftime('%Y-%m-%d %H:%M')
                    if next_run and hasattr(next_run, 'strftime'):
                        next_run = next_run.strftime('%Y-%m-%d %H:%M')
                    
                    # Get stats if available (Δ$, +, -, Total)
                    stats = row.get('stats', {})
                    delta_price = stats.get('price_changes', '')
                    added = stats.get('apartments_added', '')
                    removed = stats.get('apartments_subtracted', '')
                    total = stats.get('total_listings', '')
                    
                    # Add play button to ID column (default for Networks)
                    id_with_play = f"▶ {row_id}"
                    
                    # For Websites tab, add colored indicator based on availability_website
                    if str(current_table).lower() in ("listing_websites", "websites"):
                        avail_site = str(row.get('availability_website', '')).strip()
                        # Debug log first few rows
                        if idx < 3:
                            log_to_file(f"[Queue] Row {row_id}: availability_website='{avail_site}'")
                        
                        if avail_site and 'http' in avail_site.lower():
                            # Green light for rows with availability_website containing http
                            id_with_play = f"🟢 {row_id}"
                        else:
                            # Red light for rows without valid URL
                            id_with_play = f"🔴 {row_id}"
                    
                    # Insert into tree with zebra striping
                    tag = "even" if idx % 2 == 0 else "odd"
                    
                    # Different column structure for Websites vs Networks vs Alerts
                    if str(current_table).lower() in ("listing_websites", "websites"):
                        # Websites table: ID, Link, Metro (Seattle), Avail Website (Name/Building), Int (Avail URL)
                        # Tree columns: ID, Link, Metro, Int, Last, Next, Status, Δ$, +, -, Total, ✏️, hidden1, hidden2
                        item_id = self._queue_tree.insert("", "end", values=(
                            id_with_play,                        # ID with colored indicator
                            link,                                # Link (Website URL)
                            row.get('metro_name', 'Seattle'),   # Metro (Seattle from major_metros)
                            row.get('name', ''),                 # Int column (shows Building Name for Websites tab)
                            "",                                  # Last (empty/unused)
                            "",                                  # Next (empty/unused)
                            "",                                  # Status (empty/unused)
                            "",                                  # Δ$ (empty for websites)
                            "",                                  # + (empty for websites)
                            "",                                  # - (empty for websites)
                            "",                                  # Total (empty for websites)
                            "✏️",                               # Edit button
                            row.get('availability_website', ''), # hidden1 (stores availability_website for Activity Window check)
                            ""                                   # hidden2
                        ), tags=(tag,))
                    else:
                        # Networks table: Must provide 14 values to match tree column count
                        # Tree columns: ID, Link, Metro, Int, Last, Next, Status, Δ$, +, -, Total, ✏️, hidden1, hidden2
                        item_id = self._queue_tree.insert("", "end", values=(
                            id_with_play,    # ID with play button
                            link,            # Link
                            "",              # Metro (hidden for Networks)
                            run_interval,    # Int
                            last_run,        # Last
                            next_run,        # Next
                            status,          # Status
                            delta_price,     # Δ$
                            added,           # +
                            removed,         # -
                            total,           # Total
                            "✏️",           # Edit button
                            "",              # hidden1
                            ""               # hidden2
                        ), tags=(tag,))
                    
                    # Store error message in tooltip dictionary if exists
                    if error_msg and hasattr(self, '_cell_tooltips'):
                        # Store tooltip for status column
                        # Websites: ID, Link, Metro, Avail Website, Int, Last, Next, Status (#8)
                        # Networks: ID, Link, Int, Last, Next, Status (#6)
                        status_col = '#8' if str(current_table).lower() in ("listing_websites", "websites") else '#6'
                        self._cell_tooltips[(item_id, status_col)] = error_msg
                
                if not silent:
                    log_to_file(f"[Queue] ✓ Tree populated successfully")
                
            except Exception as e:
                log_to_file(f"[Queue] ERROR populating tree: {e}")
                import traceback
                traceback.print_exc()
            
            finally:
                # Hide loading indicator
                if hasattr(self, '_hide_loading'):
                    self._root.after(0, self._hide_loading)
                self._refresh_in_progress = False
                
        self._refresh_queue_table = _refresh_queue_table
        self._refresh_in_progress = False  # Prevent multiple simultaneous refreshes
        self._counts_refresh_in_progress = False  # Prevent multiple count refreshes
        
        # Function to refresh status counts from API
        def _refresh_status_counts(silent: bool = False):
            """Fetch status counts from API and update chips."""
            if hasattr(self, '_counts_refresh_in_progress') and self._counts_refresh_in_progress:
                return
            
            # Capture table value on main thread
            try:
                current_table = self._current_table.get()
            except Exception as e:
                log_to_file(f"[Queue] Error getting table value for counts: {e}")
                return
            
            def _bg_fetch_counts():
                counts = {'queued': 0, 'running': 0, 'done': 0, 'error': 0}
                table = current_table  # Use captured value
                
                # SKIP API call for Networks tab - data loads directly from database
                if str(current_table).lower() in ("queue_websites", "listing_websites", "websites"):
                    log_to_file(f"[Queue] Skipping API count fetch for Networks tab (loads from DB)")
                    self._counts_refresh_in_progress = False
                    return
                
                api_table = table
                lock_to_queued_only = False
                
                try:
                    self._counts_refresh_in_progress = True
                    
                    # Fetch all records (no status filter) to count them
                    api_url = f"https://api.trustyhousing.com/manual_upload/queue_website_api.php?table={api_table}&limit=1000"
                    if not silent:
                        log_to_file(f"[Queue] Fetching all records for counts from API: {api_url}")
                    
                    response = requests.get(api_url, timeout=10)
                    response.raise_for_status()
                    data = response.json()
                    
                    # Extract data array from response
                    rows = []
                    if isinstance(data, dict):
                        if 'data' in data:
                            rows = data['data']
                        elif 'rows' in data:
                            rows = data['rows']
                    elif isinstance(data, list):
                        rows = data
                    
                    # Count by status
                    for row in rows:
                        status = row.get('status', '').lower()
                        if status in counts:
                            counts[status] += 1
                    
                    if not silent:
                        log_to_file(f"[Queue] Counted {len(rows)} total records: {counts}")

                    # If Networks tab, lock the chips to show queued only
                    if lock_to_queued_only:
                        counts = {
                            'queued': counts.get('queued', 0),
                            'running': 0,
                            'done': 0,
                            'error': 0
                        }
                    
                except Exception as e:
                    log_to_file(f"[Queue] Count fetch failed: {e}")
                    log_exception("Count fetch error")
                    # Silently fail - counts not critical
                
                finally:
                    self._counts_refresh_in_progress = False
                    
                    # Update UI on main thread - update status button labels with counts
                    def _update_counts():
                        try:
                            if hasattr(self, '_status_buttons'):
                                for status_key, count_val in counts.items():
                                    if status_key in self._status_buttons:
                                        btn = self._status_buttons[status_key]
                                        # Update button text to show count
                                        status_label = status_key.capitalize()
                                        btn.config(text=f"{status_label} ({count_val})")
                            
                            # Store counts for later use
                            self._status_counts = counts
                        except Exception as e:
                            log_to_file(f"[Queue] Error updating count labels: {e}")
                    
                    if hasattr(self, '_root'):
                        self._root.after(0, _update_counts)
            
            try:
                threading.Thread(target=_bg_fetch_counts, daemon=True).start()
            except Exception as e:
                log_to_file(f"[Queue] Count thread start failed: {e}")
        
        self._refresh_status_counts = _refresh_status_counts
        
        # Check for jobs that need to be auto-queued (when next update time is reached)
        def _check_auto_queue_jobs():
            """Check all jobs and update status to 'queued' if their next update time has passed."""
            try:
                import mysql.connector
                from datetime import datetime, timedelta
                
                conn = mysql.connector.connect(
                    host='localhost',
                    user='local_uzr',
                    password='fuck',
                    database='offta',
                    port=3306,
                    connection_timeout=5
                )
                cursor = conn.cursor(dictionary=True)
                
                # Find all jobs where: status='done' AND (processed_at + run_interval_minutes) <= NOW
                cursor.execute("""
                    SELECT id, processed_at, run_interval_minutes 
                    FROM queue_websites 
                    WHERE status = 'done' 
                    AND processed_at IS NOT NULL 
                    AND run_interval_minutes > 0
                """)
                
                jobs_to_queue = []
                now = datetime.now()
                
                for row in cursor.fetchall():
                    job_id = row['id']
                    processed_at = row['processed_at']
                    interval = row['run_interval_minutes']
                    
                    if processed_at and interval:
                        next_update_time = processed_at + timedelta(minutes=int(interval))
                        if now >= next_update_time:
                            jobs_to_queue.append(job_id)
                
                # Update all jobs that are due
                if jobs_to_queue:
                    placeholders = ','.join(['%s'] * len(jobs_to_queue))
                    cursor.execute(f"""
                        UPDATE queue_websites 
                        SET status = 'queued', updated_at = NOW() 
                        WHERE id IN ({placeholders})
                    """, jobs_to_queue)
                    conn.commit()
                    log_to_file(f"[Auto-Queue] Updated {len(jobs_to_queue)} job(s) to 'queued': {jobs_to_queue}")
                
                cursor.close()
                conn.close()
                
            except Exception as e:
                log_to_file(f"[Auto-Queue] Error checking jobs: {e}")
        
        self._check_auto_queue_jobs = _check_auto_queue_jobs
        
        # Auto-refresh timer - start after 1 minute to avoid conflicts with initial load
        def _auto_refresh_tick():
            try:
                if self._queue_visible and self._auto_refresh_enabled and not self._refresh_in_progress:
                    # Silent auto refresh (no 'Loading...' or noisy logs)
                    self._refresh_queue_table(silent=True)
                
                # Also refresh counts every cycle (whether table is visible or not)
                if self._auto_refresh_enabled and not self._counts_refresh_in_progress:
                    self._refresh_status_counts(silent=True)
                
                # Check if any jobs need to be auto-queued (time is up)
                self._check_auto_queue_jobs()
            except Exception as e:
                log_to_file(f"[Queue] Auto-refresh error: {e}")
            finally:
                root.after(60000, _auto_refresh_tick)  # Schedule next check (1 minute)
        
        root.after(60000, _auto_refresh_tick)  # First check after 1 minute
        
        # Show accounts table (separate from queue/extraction)
        def _show_accounts_table(self=self):
            """Show a clean accounts-only table."""
            print("[DEBUG] _show_accounts_table called")
            log_to_file("[DEBUG] _show_accounts_table called")
            try:
                print("[DEBUG] Inside try block")
                # Create accounts frame if not exists
                if not hasattr(self, '_accounts_frame'):
                    print("[DEBUG] Creating accounts frame")
                    self._accounts_frame = tk.Frame(body, bg=chip_bg, bd=1, relief="solid", highlightthickness=1, highlightbackground=chip_border)
                    
                    # Header with search
                    acc_header = tk.Frame(self._accounts_frame, bg=chip_bg)
                    acc_header.pack(fill="x", padx=4, pady=4)
                    
                    tk.Label(acc_header, text="Accounts", fg=fg, bg=chip_bg, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(4, 12))
                    tk.Label(acc_header, text="Search:", fg=muted, bg=chip_bg, font=("Segoe UI", 9)).pack(side="left")
                    
                    self._accounts_search_var2 = tk.StringVar(master=root, value="")
                    tk.Entry(acc_header, textvariable=self._accounts_search_var2, width=20).pack(side="left", padx=4)
                    tk.Button(acc_header, text="Go", bg=accent, fg=bg, padx=8, pady=2, font=("Segoe UI", 8, "bold"), relief="flat",
                             command=lambda: _load_accounts()).pack(side="left")
                    
                    # Table
                    acc_tree_frame = tk.Frame(self._accounts_frame, bg=chip_bg)
                    acc_tree_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
                    
                    acc_cols = ("ID", "Username", "Email", "Name", "Role", "Registered", "Last Seen")
                    self._accounts_tree = ttk.Treeview(acc_tree_frame, columns=acc_cols, show="headings", height=12)
                    
                    # Configure row tags for zebra striping (same as extraction table)
                    try:
                        self._accounts_tree.tag_configure("even", background="#FFFFFF")      # white
                        self._accounts_tree.tag_configure("odd", background="#E6F7FF")       # light blue
                    except Exception:
                        pass
                    
                    widths = [50, 120, 180, 150, 80, 130, 130]
                    for c, w in zip(acc_cols, widths):
                        self._accounts_tree.heading(c, text=c)
                        self._accounts_tree.column(c, width=w, anchor="w")
                    
                    # Double-click to open email
                    def _on_acc_dblclick(event):
                        try:
                            item = self._accounts_tree.identify_row(event.y)
                            if item:
                                values = self._accounts_tree.item(item, "values")
                                if values and len(values) > 2:
                                    email = str(values[2] or "").strip()
                                    if email and '@' in email:
                                        import webbrowser
                                        webbrowser.open_new_tab(f"mailto:{email}")
                        except Exception as e:
                            log_to_file(f"[Accounts] Double-click error: {e}")
                    
                    self._accounts_tree.bind("<Double-1>", _on_acc_dblclick)
                    
                    scroll = ttk.Scrollbar(acc_tree_frame, orient="vertical", command=self._accounts_tree.yview)
                    self._accounts_tree.configure(yscrollcommand=scroll.set)
                    self._accounts_tree.pack(side="left", fill="both", expand=True)
                    scroll.pack(side="right", fill="y")
                    
                    # Status bar - CREATE BEFORE using in _load_accounts
                    self._accounts_status = tk.Label(self._accounts_frame, text="Ready", fg=muted, bg=chip_bg, font=("Consolas", 8))
                    self._accounts_status.pack(fill="x", padx=4, pady=(0, 4))
                
                # Load accounts data
                def _load_accounts():
                    # Ensure status label exists
                    if not hasattr(self, '_accounts_status'):
                        log_to_file("[Accounts] Status label not created yet, skipping")
                        return
                    
                    def _bg_load():
                        error_msg = None
                        accs = []
                        term = ""
                        try:
                            log_to_file("[Accounts] Background load started")
                            term = (self._accounts_search_var2.get().strip() if hasattr(self, '_accounts_search_var2') else "")
                            log_to_file(f"[Accounts] Search term: '{term}'")
                            
                            # Use API instead of direct MySQL connection (more reliable)
                            api_url = php_url("step5/get_accounts.php")
                            if term:
                                api_url += f"?search={term}"
                            
                            log_to_file(f"[Accounts] Calling API: {api_url}")
                            import requests
                            response = requests.get(api_url, timeout=10)
                            log_to_file(f"[Accounts] API response status: {response.status_code}")
                            
                            if response.status_code == 200:
                                try:
                                    data = response.json()
                                except Exception as je:
                                    snippet = response.text[:500] if hasattr(response, 'text') else '<no text>'
                                    log_to_file(f"[Accounts] JSON parse failed: {je}. Snippet: {snippet}")
                                    error_msg = f"Invalid JSON from API"
                                    data = None
                                if data and data.get('ok'):
                                    accs = data.get('accounts', [])
                                    log_to_file(f"[Accounts] Fetched {len(accs)} accounts")
                                elif data:
                                    error_msg = data.get('error', 'Unknown API error')
                                    log_to_file(f"[Accounts] API error: {error_msg}")
                            else:
                                error_msg = f"API returned status {response.status_code}"
                                log_to_file(f"[Accounts] {error_msg}")
                            
                        except Exception as e:
                            error_msg = f"Error: {str(e)[:100]}"
                            log_to_file(f"[Accounts] Load error: {type(e).__name__}: {e}")
                            log_exception("Accounts load error")
                        
                        def _update_ui():
                            try:
                                log_to_file("[Accounts] UI update started")
                                if error_msg:
                                    if hasattr(self, '_accounts_status'):
                                        self._accounts_status.config(text=f"✗ {error_msg}")
                                    log_to_file(f"[Accounts] Showing error: {error_msg}")
                                    return
                                
                                if hasattr(self, '_accounts_tree'):
                                    for item in self._accounts_tree.get_children():
                                        self._accounts_tree.delete(item)
                                    log_to_file("[Accounts] Tree cleared")
                                    
                                    for i, a in enumerate(accs):
                                        try:
                                            full_name = f"{a.get('first_name') or ''} {a.get('last_name') or ''}".strip()
                                            reg = str(a.get('registered') or '-')
                                            seen = str(a.get('last_seen') or '-')
                                            
                                            # Apply zebra striping (same as extraction table)
                                            zebra_tag = "odd" if (i % 2 == 1) else "even"
                                            
                                            self._accounts_tree.insert("", "end", values=(
                                                a.get('id'),
                                                a.get('username') or '-',
                                                a.get('email') or '-',
                                                full_name or '-',
                                                a.get('role') or '-',
                                                reg,
                                                seen
                                            ), tags=(zebra_tag,))
                                        except Exception as row_err:
                                            log_to_file(f"[Accounts] Row {i} insert error: {row_err}")
                                    
                                    log_to_file(f"[Accounts] Inserted {len(accs)} rows")
                                
                                if hasattr(self, '_accounts_status'):
                                    self._accounts_status.config(text=f"✓ Loaded {len(accs)} accounts" + (f" (search: '{term}')" if term else ""))
                                log_to_file("[Accounts] UI update complete")
                            except Exception as e:
                                log_to_file(f"[Accounts] UI update error: {e}")
                                log_exception("Accounts UI update error")
                                try:
                                    if hasattr(self, '_accounts_status'):
                                        self._accounts_status.config(text=f"UI Error: {e}")
                                except Exception:
                                    pass
                        
                        try:
                            if hasattr(self, '_root'):
                                self._root.after(0, _update_ui)
                                log_to_file("[Accounts] UI update scheduled via self._root")
                            else:
                                root.after(0, _update_ui)
                                log_to_file("[Accounts] UI update scheduled via root")
                        except Exception as e:
                            log_to_file(f"[Accounts] Failed to schedule UI update: {e}")
                            log_exception("Schedule UI update error")
                    
                    try:
                        self._accounts_status.config(text="Loading...")
                        log_to_file("[Accounts] Starting background thread")
                        threading.Thread(target=_bg_load, daemon=True).start()
                        log_to_file("[Accounts] Background thread started")
                    except Exception as e:
                        log_to_file(f"[Accounts] Failed to start thread: {e}")
                        log_exception("Accounts thread start error")
                        self._accounts_status.config(text=f"Error: {e}")
                
                # Show frame
                self._accounts_frame.pack(fill="both", expand=True, padx=8, pady=(6, 0))
                self._accounts_visible = True
                
                # Resize window
                sw = root.winfo_screenwidth()
                new_h = 500
                new_w = 900
                x_pos = int(sw * 0.20)  # 20% from left edge
                y_pos = 0  # Top of screen
                root.geometry(f"{new_w}x{new_h}+{x_pos}+{y_pos}")
                root.resizable(True, True)
                
                # Load initial data
                log_to_file("[Accounts] Calling _load_accounts()")
                _load_accounts()
                log_to_file("[Accounts] Table shown successfully")
                
            except Exception as e:
                log_to_file(f"[Accounts] Show table error: {e}")
                log_exception("Show accounts table")
                # Try to show error in status if available
                try:
                    if hasattr(self, '_accounts_status'):
                        self._accounts_status.config(text=f"Error: {e}")
                except Exception:
                    pass
        
        self._show_accounts_table = _show_accounts_table
        self._accounts_visible = False
        
        # Show Notifications (Alerts Preset) table
        def _show_notifications_table(self=self):
            """Show alerts preset table."""
            print("[DEBUG] _show_notifications_table called")
            log_to_file("[DEBUG] _show_notifications_table called")
            try:
                # Create notifications frame if not exists
                if not hasattr(self, '_notifications_frame'):
                    print("[DEBUG] Creating notifications frame")
                    self._notifications_frame = tk.Frame(body, bg=chip_bg, bd=1, relief="solid", highlightthickness=1, highlightbackground=chip_border)
                    
                    # Header
                    notif_header = tk.Frame(self._notifications_frame, bg=chip_bg)
                    notif_header.pack(fill="x", padx=4, pady=4)
                    
                    tk.Label(notif_header, text="Alerts Preset", fg=fg, bg=chip_bg, font=("Segoe UI", 10, "bold")).pack(side="left", padx=(4, 12))
                    
                    # Refresh button
                    tk.Button(notif_header, text="⟳ Refresh", bg=accent, fg=bg, padx=8, pady=2, font=("Segoe UI", 8, "bold"), relief="flat",
                             command=lambda: _load_alerts()).pack(side="left")
                    
                    # Table
                    notif_tree_frame = tk.Frame(self._notifications_frame, bg=chip_bg)
                    notif_tree_frame.pack(fill="both", expand=True, padx=4, pady=(0, 4))
                    
                    notif_cols = ("ID", "Type", "Title", "Subtitle", "Body", "Sent Every", "Day & Time", "Action", "Delay (sec)", "Platforms", "Email")
                    self._notifications_tree = ttk.Treeview(notif_tree_frame, columns=notif_cols, show="headings", height=12)
                    
                    # Configure row tags for zebra striping
                    try:
                        self._notifications_tree.tag_configure("even", background="#FFFFFF")
                        self._notifications_tree.tag_configure("odd", background="#E6F7FF")
                    except Exception:
                        pass
                    
                    widths = [40, 50, 140, 160, 180, 80, 110, 80, 80, 90, 120]
                    for c, w in zip(notif_cols, widths):
                        self._notifications_tree.heading(c, text=c)
                        self._notifications_tree.column(c, width=w, anchor="w")
                    
                    # Double-click to edit (placeholder for now)
                    def _on_notif_dblclick(event):
                        try:
                            item = self._notifications_tree.identify_row(event.y)
                            if item:
                                values = self._notifications_tree.item(item, "values")
                                if values:
                                    log_to_file(f"[Notifications] Double-clicked alert ID: {values[0]}")
                                    # TODO: Add edit dialog here
                        except Exception as e:
                            log_to_file(f"[Notifications] Double-click error: {e}")
                    
                    self._notifications_tree.bind("<Double-1>", _on_notif_dblclick)
                    
                    scroll = ttk.Scrollbar(notif_tree_frame, orient="vertical", command=self._notifications_tree.yview)
                    self._notifications_tree.configure(yscrollcommand=scroll.set)
                    self._notifications_tree.pack(side="left", fill="both", expand=True)
                    scroll.pack(side="right", fill="y")
                    
                    # Status bar
                    self._notifications_status = tk.Label(self._notifications_frame, text="Ready", fg=muted, bg=chip_bg, font=("Consolas", 8))
                    self._notifications_status.pack(fill="x", padx=4, pady=(0, 4))
                
                # Load alerts data
                def _load_alerts():
                    if not hasattr(self, '_notifications_status'):
                        log_to_file("[Notifications] Status label not created yet, skipping")
                        return
                    
                    def _bg_load():
                        error_msg = None
                        alerts = []
                        try:
                            import mysql.connector
                            
                            def _ui_status(msg):
                                if hasattr(self, '_notifications_status'):
                                    self._root.after(0, lambda: self._notifications_status.config(text=msg))
                            
                            _ui_status("Loading alerts...")
                            
                            conn = mysql.connector.connect(
                                host='localhost',
                                port=3306,
                                user='root',
                                password='',
                                database='offta',
                                connect_timeout=10
                            )
                            cursor = conn.cursor(dictionary=True)
                            cursor.execute("""
                                SELECT id, type, title, subtitle, body, Sent_every, 
                                       Day_and_Time, Action, sent_delay_in_sec, 
                                       platforms, html_email
                                FROM alerts_preset
                                ORDER BY id ASC
                            """)
                            alerts = cursor.fetchall()
                            cursor.close()
                            conn.close()
                            
                            log_to_file(f"[Notifications] Loaded {len(alerts)} alert presets")
                            
                        except Exception as e:
                            error_msg = f"Load failed: {str(e)[:60]}"
                            log_to_file(f"[Notifications] {error_msg}")
                        
                        # Update UI on main thread
                        def _fill_tree():
                            try:
                                # Clear tree
                                for item in self._notifications_tree.get_children():
                                    self._notifications_tree.delete(item)
                                
                                # Insert rows
                                for idx, alert in enumerate(alerts):
                                    tag = "even" if idx % 2 == 0 else "odd"
                                    self._notifications_tree.insert("", "end", values=(
                                        alert.get('id', ''),
                                        alert.get('type', ''),
                                        alert.get('title', ''),
                                        alert.get('subtitle', ''),
                                        alert.get('body', ''),
                                        alert.get('Sent_every', ''),
                                        alert.get('Day_and_Time', ''),
                                        alert.get('Action', ''),
                                        alert.get('sent_delay_in_sec', ''),
                                        alert.get('platforms', ''),
                                        alert.get('html_email', '')
                                    ), tags=(tag,))
                                
                                if hasattr(self, '_notifications_status'):
                                    self._notifications_status.config(text=f"Loaded {len(alerts)} alert presets")
                            except Exception as e:
                                log_to_file(f"[Notifications] Tree fill error: {e}")
                                if hasattr(self, '_notifications_status'):
                                    self._notifications_status.config(text=f"Error: {e}")
                        
                        self._root.after(0, _fill_tree)
                    
                    # Run in background thread
                    import threading
                    threading.Thread(target=_bg_load, daemon=True).start()
                
                # Show frame and load data
                if not hasattr(self, '_notifications_visible') or not self._notifications_visible:
                    print("[DEBUG] Packing notifications frame")
                    self._notifications_frame.pack(fill="both", expand=True, padx=8, pady=8)
                    self._notifications_visible = True
                    
                    # Resize window
                    try:
                        self._root.geometry("1150x550+273+0")
                    except Exception:
                        pass
                    
                    # Load data
                    _load_alerts()
                else:
                    # Already visible, just refresh
                    _load_alerts()
                
            except Exception as e:
                log_to_file(f"[Notifications] Show table error: {e}")
                import traceback
                traceback.print_exc()
                try:
                    if hasattr(self, '_notifications_status'):
                        self._notifications_status.config(text=f"Error: {e}")
                except Exception:
                    pass
        
        self._show_notifications_table = _show_notifications_table
        self._notifications_visible = False
        
        # Toggle queue table visibility
        def _toggle_queue_table(status_filter=None):
            """Toggle queue table with maximum error protection."""
            def log_both(msg):
                """Log to both console and file."""
                print(msg)
                log_to_file(msg)
            
            try:
                log_both(f"\n[Queue] ========== TOGGLE START ==========")
                log_both(f"[Queue] status_filter={status_filter}")
                log_both(f"[Queue] current _queue_visible={getattr(self, '_queue_visible', 'NOT SET')}")
                log_both(f"[Queue] _queue_frame exists={hasattr(self, '_queue_frame')}")
                
                # Safety check
                if not hasattr(self, '_queue_frame'):
                    log_both("[Queue] FATAL: _queue_frame not initialized!")
                    return
                
                # Toggle state
                new_state = not getattr(self, '_queue_visible', False)
                self._queue_visible = new_state
                log_both(f"[Queue] New state will be: {new_state}")
                
                if new_state:  # SHOWING queue
                    log_both("[Queue] Showing queue table...")
                    
                    # Set status filter if provided
                    if status_filter:
                        log_both(f"[Queue] Setting status filter to: {status_filter}")
                        self._current_status.set(status_filter)
                    
                    # Hide logs first (mutual exclusion)
                    try:
                        if hasattr(self, '_logs_visible') and self._logs_visible:
                            log_both("[Queue] Hiding logs...")
                            if hasattr(self, '_ai_frame'):
                                self._ai_frame.pack_forget()
                            self._logs_visible = False
                    except Exception as e:
                        log_both(f"[Queue] Warning - couldn't hide logs: {e}")
                        log_exception("Hide logs error")
                    
                    # Show queue frame - CRITICAL OPERATION
                    try:
                        log_both("[Queue] About to pack _queue_frame...")
                        self._queue_frame.pack(fill="both", expand=True, padx=8, pady=(6, 0))
                        log_both("[Queue] ✓ Frame packed successfully")
                    except Exception as e:
                        log_both(f"[Queue] ERROR packing frame: {e}")
                        log_exception("Pack frame error")
                        self._queue_visible = False  # Revert state
                        return
                    
                    # Resize window - CRITICAL OPERATION
                    try:
                        log_both("[Queue] About to resize window...")
                        sw = root.winfo_screenwidth()
                        new_h = 500
                        new_w = 1050  # Adjusted width for 11 columns (merged Last Run + Time Ago)
                        x_pos = int(sw * 0.20)  # 20% from left edge
                        y_pos = 0  # Top of screen
                        log_both(f"[Queue] New geometry: {new_w}x{new_h}+{x_pos}+{y_pos}")
                        root.geometry(f"{new_w}x{new_h}+{x_pos}+{y_pos}")
                        root.resizable(True, True)
                        log_both("[Queue] ✓ Window resized successfully")
                    except Exception as e:
                        log_both(f"[Queue] ERROR resizing: {e}")
                        log_exception("Resize window error")
                        # Don't return - continue anyway
                    
                    # Load data - CRITICAL OPERATION
                    try:
                        log_both("[Queue] About to refresh table data...")
                        self._refresh_queue_table()
                        log_both("[Queue] ✓ Refresh triggered successfully")
                    except Exception as e:
                        log_both(f"[Queue] ERROR refreshing: {e}")
                        log_exception("Refresh table error")
                        # Don't return - table is visible even if empty
                    
                    # Load counts - NON-CRITICAL
                    try:
                        log_both("[Queue] Refreshing status counts...")
                        if hasattr(self, '_refresh_status_counts'):
                            self._refresh_status_counts()
                    except Exception as e:
                        log_both(f"[Queue] Count refresh error: {e}")
                        # Don't fail if counts don't load
                    
                else:  # HIDING queue
                    log_both("[Queue] Hiding queue table...")
                    
                    # Hide frame
                    try:
                        log_both("[Queue] About to pack_forget...")
                        self._queue_frame.pack_forget()
                        log_both("[Queue] ✓ Frame hidden successfully")
                    except Exception as e:
                        log_both(f"[Queue] ERROR hiding frame: {e}")
                        log_exception("Hide frame error")
                    
                    # Shrink window
                    try:
                        log_both("[Queue] About to shrink window...")
                        sw = root.winfo_screenwidth()
                        new_h = 120
                        new_w = 360
                        x_pos = int(sw * 0.20)  # 20% from left edge
                        y_pos = 0  # Top of screen
                        log_both(f"[Queue] New geometry: {new_w}x{new_h}+{x_pos}+{y_pos}")
                        root.geometry(f"{new_w}x{new_h}+{x_pos}+{y_pos}")
                        root.resizable(False, False)
                        log_both("[Queue] ✓ Window shrunk successfully")
                    except Exception as e:
                        log_both(f"[Queue] ERROR shrinking: {e}")
                        log_exception("Shrink window error")
                
                log_both(f"[Queue] ========== TOGGLE END ==========\n")
                
            except Exception as ex:
                log_both(f"\n[Queue] !!!!! CATASTROPHIC ERROR !!!!!")
                log_both(f"[Queue] Exception: {ex}")
                log_exception("CATASTROPHIC TOGGLE ERROR")
                log_both(f"[Queue] !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
                # Try to reset state
                try:
                    self._queue_visible = False
                except:
                    pass
        
        # Bind chip clicks to toggle table with status filter
        def make_chip_clickable(chip_widget, status_val):
            def on_click(_e):
                try:
                    if not hasattr(self, '_queue_visible'):
                        self._queue_visible = False
                    
                    if not self._queue_visible:
                        self._current_status.set(status_val)
                        _toggle_queue_table(status_val)
                    else:
                        self._current_status.set(status_val)
                        self._refresh_queue_table()
                except Exception as ex:
                    print(f"Chip click error: {ex}")
                    import traceback
                    traceback.print_exc()
            
            try:
                chip_widget.bind("<Button-1>", on_click)
                for child in chip_widget.winfo_children():
                    child.bind("<Button-1>", on_click)
            except Exception as ex:
                print(f"Chip binding error: {ex}")
        
        # Store job data by ID for easy lookup
        self._job_data_cache = {}
        
        # Stats chips removed - no longer binding click events
        
        # Bind Extractor button to toggle queue table
        def _on_extractor_btn(_e):
            try:
                log_to_file("[Queue] Extractor button clicked")
                print("[Queue] Extractor button clicked")
                
                # Hide accounts table if visible
                if hasattr(self, '_accounts_visible') and self._accounts_visible:
                    try:
                        self._accounts_frame.pack_forget()
                        self._accounts_visible = False
                    except Exception:
                        pass
                
                # Hide notifications table if visible
                if hasattr(self, '_notifications_visible') and self._notifications_visible:
                    try:
                        self._notifications_frame.pack_forget()
                        self._notifications_visible = False
                    except Exception:
                        pass
                
                _toggle_queue_table()
            except Exception as ex:
                log_to_file(f"[Queue] Extractor button handler error: {ex}")
                log_exception("Extractor button handler error")
                print(f"[Queue] Extractor button handler error: {ex}")
        extractor_btn.bind("<Button-1>", _on_extractor_btn)
        
        # Bind Accounts button - show CLEAN accounts-only table (separate from queue/extraction)
        def _on_accounts_btn(_e):
            try:
                log_to_file("[Accounts] Accounts button clicked")
                print("[Accounts] Accounts button clicked")
                
                # Hide queue table if visible
                if hasattr(self, '_queue_visible') and self._queue_visible:
                    try:
                        self._queue_frame.pack_forget()
                        self._queue_visible = False
                    except Exception:
                        pass
                
                # Hide logs if visible
                if hasattr(self, '_logs_visible') and self._logs_visible:
                    try:
                        self._ai_frame.pack_forget()
                        self._logs_visible = False
                    except Exception:
                        pass
                
                # Show accounts table
                self._show_accounts_table()
                
            except Exception as ex:
                log_to_file(f"[Accounts] Accounts button handler error: {ex}")
                log_exception("Accounts button handler error")
                print(f"[Accounts] Accounts button handler error: {ex}")
        accounts_btn.bind("<Button-1>", _on_accounts_btn)
        
        # Bind Mailer button - newsletter management
        def _on_mailer_btn(_e):
            try:
                log_to_file("[Mailer] Mailer button clicked")
                print("[Mailer] Mailer button clicked")
                
                # Hide queue table if visible
                if hasattr(self, '_queue_visible') and self._queue_visible:
                    try:
                        self._queue_frame.pack_forget()
                        self._queue_visible = False
                    except Exception:
                        pass
                
                # Hide accounts table if visible
                if hasattr(self, '_accounts_visible') and self._accounts_visible:
                    try:
                        self._accounts_frame.pack_forget()
                        self._accounts_visible = False
                    except Exception:
                        pass
                
                # Hide logs if visible
                if hasattr(self, '_logs_visible') and self._logs_visible:
                    try:
                        self._ai_frame.pack_forget()
                        self._logs_visible = False
                    except Exception:
                        pass
                
                # Toggle mailer table
                self._toggle_mailer_table()
                
            except Exception as ex:
                log_to_file(f"[Mailer] Mailer button handler error: {ex}")
                log_exception("Mailer button handler error")
                print(f"[Mailer] Mailer button handler error: {ex}")
        mailer_btn.bind("<Button-1>", _on_mailer_btn)
        
        # Bind Notifications button
        def _on_notifications_btn(_e):
            try:
                log_to_file("[Notifications] Notifications button clicked")
                print("[Notifications] Notifications button clicked")
                
                # Hide queue table if visible
                if hasattr(self, '_queue_visible') and self._queue_visible:
                    try:
                        self._queue_frame.pack_forget()
                        self._queue_visible = False
                    except Exception:
                        pass
                
                # Hide accounts table if visible
                if hasattr(self, '_accounts_visible') and self._accounts_visible:
                    try:
                        self._accounts_frame.pack_forget()
                        self._accounts_visible = False
                    except Exception:
                        pass
                
                # Hide logs if visible
                if hasattr(self, '_logs_visible') and self._logs_visible:
                    try:
                        self._ai_frame.pack_forget()
                        self._logs_visible = False
                    except Exception:
                        pass
                
                # Toggle notifications table
                self._show_notifications_table()
                
            except Exception as ex:
                log_to_file(f"[Notifications] Notifications button handler error: {ex}")
                print(f"[Notifications] Notifications button handler error: {ex}")
        notifications_btn.bind("<Button-1>", _on_notifications_btn)
        
        # Bind Sync DB button - uploads affected tables to remote server
        def _on_sync_btn(_e):
            try:
                log_to_file("[Sync] Sync DB button clicked")
                print("[Sync] Sync DB button clicked")
                
                from tkinter import messagebox, ttk
                import subprocess
                import tempfile
                import os
                from datetime import datetime
                import mysql.connector
                
                # MySQL tools paths (XAMPP)
                mysqldump_path = r"C:\xampp\mysql\bin\mysqldump.exe"
                mysql_path = r"C:\xampp\mysql\bin\mysql.exe"
                
                # Check if MySQL tools exist
                if not os.path.exists(mysqldump_path):
                    messagebox.showerror(
                        "MySQL Not Found",
                        f"mysqldump not found at:\n{mysqldump_path}\n\nPlease verify XAMPP MySQL installation.",
                        parent=root
                    )
                    return
                
                if not os.path.exists(mysql_path):
                    messagebox.showerror(
                        "MySQL Not Found",
                        f"mysql not found at:\n{mysql_path}\n\nPlease verify XAMPP MySQL installation.",
                        parent=root
                    )
                    return
                
                # Step 1: Show preloader and test remote connection
                log_to_file("[Sync] Testing connection to remote database...")
                self._set_last_line("[Sync] Connecting to remote...", "muted")
                
                # Create preloader window
                preloader = tk.Toplevel(root)
                preloader.title("Database Sync")
                preloader.geometry("400x150")
                preloader.transient(root)
                preloader.grab_set()
                preloader.resizable(False, False)
                
                # Center the preloader
                preloader.update_idletasks()
                x = root.winfo_x() + (root.winfo_width() // 2) - (400 // 2)
                y = root.winfo_y() + (root.winfo_height() // 2) - (150 // 2)
                preloader.geometry(f"400x150+{x}+{y}")
                
                preloader_frame = tk.Frame(preloader, bg="#2C3E50")
                preloader_frame.pack(fill="both", expand=True, padx=20, pady=20)
                
                status_label = tk.Label(
                    preloader_frame,
                    text="🔄 Connecting to remote database...",
                    font=("Segoe UI", 11, "bold"),
                    bg="#2C3E50",
                    fg="white"
                )
                status_label.pack(pady=10)
                
                detail_label = tk.Label(
                    preloader_frame,
                    text="Server: 172.104.206.182:3306",
                    font=("Segoe UI", 9),
                    bg="#2C3E50",
                    fg="#BDC3C7"
                )
                detail_label.pack()
                
                # Progress bar
                from tkinter import ttk
                progress_bar = ttk.Progressbar(
                    preloader_frame,
                    mode='determinate',
                    length=350,
                    style='Custom.Horizontal.TProgressbar'
                )
                progress_bar.pack(pady=15)
                
                progress_label = tk.Label(
                    preloader_frame,
                    text="Step 1 of 3: Connecting...",
                    font=("Segoe UI", 9),
                    bg="#2C3E50",
                    fg="#95A5A6"
                )
                progress_label.pack()
                
                # Configure progress bar style
                style = ttk.Style()
                style.theme_use('default')
                style.configure(
                    'Custom.Horizontal.TProgressbar',
                    background='#3498DB',
                    troughcolor='#1A1D20',
                    borderwidth=0,
                    thickness=8
                )
                
                progress_bar['value'] = 0
                preloader.update()
                
                try:
                    # Test connection with longer timeout
                    progress_bar['value'] = 10
                    status_label.config(text="🔗 Testing connection...")
                    detail_label.config(text="This may take up to 30 seconds...")
                    progress_label.config(text="Step 1 of 3: Connecting...")
                    preloader.update()
                    
                    test_conn = mysql.connector.connect(
                        host="172.104.206.182",
                        port=3306,
                        user="seattlelisted_usr",
                        password="T@5z6^pl}",
                        database="offta",
                        connect_timeout=30,
                        connection_timeout=30
                    )
                    test_conn.close()
                    
                    progress_bar['value'] = 33
                    status_label.config(text="✓ Connection successful!")
                    detail_label.config(text="Fetching database information...", fg="#2ECC71")
                    progress_label.config(text="Step 2 of 3: Discovering tables...")
                    preloader.update()
                    
                    log_to_file("[Sync] ✓ Remote database connection successful")
                    self._set_last_line("[Sync] ✓ Connected to remote", "ok")
                    
                except Exception as conn_err:
                    preloader.destroy()
                    log_to_file(f"[Sync] ✗ Cannot connect to remote database: {conn_err}")
                    self._set_last_line("[Sync] ✗ Connection failed", "err")
                    messagebox.showerror(
                        "Remote Database Unavailable",
                        f"Cannot connect to remote database:\n\n" +
                        f"Server: 172.104.206.182:3306\n" +
                        f"Database: offta\n" +
                        f"Error: {conn_err}\n\n" +
                        "Please check:\n" +
                        "• Network connectivity\n" +
                        "• MySQL server is running\n" +
                        "• User has remote access permissions\n" +
                        "• Firewall allows port 3306",
                        parent=root
                    )
                    return
                
                # Step 2: Get list of all tables and compare databases
                progress_bar['value'] = 40
                status_label.config(text="📊 Discovering tables...")
                detail_label.config(text="Fetching table list...", fg="#3498DB")
                progress_label.config(text="Step 2 of 3: Fetching tables...")
                preloader.update()
                
                log_to_file("[Sync] Discovering all tables...")
                self._set_last_line("[Sync] Fetching table list...", "muted")
                
                table_diffs = []
                remote_available = False
                
                try:
                    # Connect to local database
                    local_conn = mysql.connector.connect(
                        host="localhost",
                        user="root",
                        password="",
                        database="offta"
                    )
                    local_cursor = local_conn.cursor()
                    
                    # Get all tables from local database
                    local_cursor.execute("SHOW TABLES")
                    local_tables = {row[0] for row in local_cursor.fetchall()}
                    log_to_file(f"[Sync] Found {len(local_tables)} tables in local database")
                    
                    # Connect to remote database
                    remote_tables = set()
                    try:
                        remote_conn = mysql.connector.connect(
                            host="172.104.206.182",
                            port=3306,
                            user="seattlelisted_usr",
                            password="T@5z6^pl}",
                            database="offta",
                            connect_timeout=30,
                            connection_timeout=30
                        )
                        remote_cursor = remote_conn.cursor()
                        remote_available = True
                        
                        # Get all tables from remote database
                        remote_cursor.execute("SHOW TABLES")
                        remote_tables = {row[0] for row in remote_cursor.fetchall()}
                        log_to_file(f"[Sync] Found {len(remote_tables)} tables in remote database")
                        log_to_file("[Sync] ✓ Connected to remote database for comparison")
                    except Exception as remote_err:
                        log_to_file(f"[Sync] ⚠️ Cannot connect to remote database: {remote_err}")
                        remote_available = False
                    
                    # Get union of all tables from both databases
                    all_tables = sorted(local_tables | remote_tables)
                    log_to_file(f"[Sync] Total unique tables: {len(all_tables)}")
                    
                    progress_bar['value'] = 60
                    status_label.config(text="📊 Comparing databases...")
                    detail_label.config(text=f"Analyzing {len(all_tables)} tables...", fg="#3498DB")
                    progress_label.config(text=f"Step 3 of 3: Comparing {len(all_tables)} tables...")
                    preloader.update()
                    
                    # Collect row counts
                    for table in all_tables:
                        try:
                            # Get local count (if table exists locally)
                            if table in local_tables:
                                local_cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                                local_count = local_cursor.fetchone()[0]
                            else:
                                local_count = 0
                            
                            # Get remote count if available
                            if remote_available:
                                try:
                                    if table in remote_tables:
                                        remote_cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                                        remote_count = remote_cursor.fetchone()[0]
                                    else:
                                        remote_count = 0  # Table doesn't exist yet
                                        log_to_file(f"[Sync] Table {table} doesn't exist on remote (will be created)")
                                except Exception as table_err:
                                    log_to_file(f"[Sync] Warning: Could not get remote count for {table}: {table_err}")
                                    remote_count = '?'
                            else:
                                remote_count = '?'
                            
                            if isinstance(remote_count, int) and isinstance(local_count, int):
                                diff = local_count - remote_count
                            else:
                                diff = '?'
                            
                            table_diffs.append({
                                'table': table,
                                'local': local_count,
                                'remote': remote_count,
                                'diff': diff
                            })
                        except Exception as table_err:
                            log_to_file(f"[Sync] Warning: Could not compare {table}: {table_err}")
                            table_diffs.append({
                                'table': table,
                                'local': '?',
                                'remote': '?',
                                'diff': '?'
                            })
                    
                    local_cursor.close()
                    local_conn.close()
                    if remote_available:
                        remote_cursor.close()
                        remote_conn.close()
                    
                    log_to_file("[Sync] Database comparison complete")
                    
                    # Close preloader
                    progress_bar['value'] = 100
                    status_label.config(text="✓ Analysis complete!")
                    detail_label.config(text=f"Found {len(table_diffs)} tables", fg="#2ECC71")
                    progress_label.config(text="Complete! Opening comparison window...", fg="#2ECC71")
                    preloader.update()
                    root.after(500)  # Brief pause to show success
                    preloader.destroy()
                    
                except Exception as compare_err:
                    preloader.destroy()
                    log_to_file(f"[Sync] ✗ Failed to compare databases: {compare_err}")
                    messagebox.showerror(
                        "Sync Failed",
                        f"Failed to access local database:\n\n{compare_err}",
                        parent=root
                    )
                    return
                
                # Step 3: Create inline sync status window
                compare_win = tk.Toplevel(root)
                compare_win.title("Database Sync Control")
                compare_win.geometry("800x600")
                compare_win.transient(root)
                compare_win.resizable(True, True)
                
                # Header
                header_frame = tk.Frame(compare_win, bg="#2C3E50", pady=10)
                header_frame.pack(fill="x")
                
                tk.Label(
                    header_frame,
                    text="� Database Sync Control",
                    font=("Segoe UI", 14, "bold"),
                    bg="#2C3E50",
                    fg="white"
                ).pack()
                
                # Stats summary
                total_local = sum(d['local'] for d in table_diffs if isinstance(d['local'], int))
                total_remote = sum(d['remote'] for d in table_diffs if isinstance(d['remote'], int))
                
                tk.Label(
                    header_frame,
                    text=f"{len(table_diffs)} tables  •  {total_local:,} local rows  •  {total_remote:,} remote rows",
                    font=("Segoe UI", 9),
                    bg="#2C3E50",
                    fg="#ECF0F1"
                ).pack()
                
                # Button frame
                button_frame = tk.Frame(compare_win, bg="white", pady=15)
                button_frame.pack(fill="x", padx=20, pady=(15, 10))
                
                # Status label and progress bar
                status_label = tk.Label(
                    compare_win,
                    text="Ready to sync",
                    font=("Segoe UI", 10),
                    bg="white",
                    fg="#7F8C8D"
                )
                status_label.pack(pady=(0, 5))
                
                progress_bar = ttk.Progressbar(compare_win, mode='indeterminate', length=450)
                progress_bar.pack(pady=5)
                progress_bar.pack_forget()  # Hide initially
                
                # Create notebook for tabs
                notebook = ttk.Notebook(compare_win)
                notebook.pack(fill="both", expand=True, padx=10, pady=10)
                
                # Tab 1: Tables view
                tables_tab = tk.Frame(notebook, bg="white")
                notebook.add(tables_tab, text="📊 Tables")
                
                # Create canvas for scrollable table
                canvas = tk.Canvas(tables_tab, bg="white")
                scrollbar = ttk.Scrollbar(tables_tab, orient="vertical", command=canvas.yview)
                scrollable_frame = tk.Frame(canvas, bg="white")
                
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                
                # Header row
                header_frame = tk.Frame(scrollable_frame, bg="#34495E", relief="flat")
                header_frame.pack(fill="x", pady=(0, 2))
                
                tk.Label(header_frame, text="Table Name", bg="#34495E", fg="white", 
                        font=("Segoe UI", 9, "bold"), width=20, anchor="w").pack(side="left", padx=5, pady=5)
                tk.Label(header_frame, text="Local Rows", bg="#34495E", fg="white",
                        font=("Segoe UI", 9, "bold"), width=10, anchor="center").pack(side="left", padx=5, pady=5)
                tk.Label(header_frame, text="Remote Rows", bg="#34495E", fg="white",
                        font=("Segoe UI", 9, "bold"), width=10, anchor="center").pack(side="left", padx=5, pady=5)
                tk.Label(header_frame, text="Difference", bg="#34495E", fg="white",
                        font=("Segoe UI", 9, "bold"), width=15, anchor="center").pack(side="left", padx=5, pady=5)
                tk.Label(header_frame, text="Actions", bg="#34495E", fg="white",
                        font=("Segoe UI", 9, "bold"), width=10, anchor="center").pack(side="left", padx=5, pady=5)
                
                # Function to get tables with their foreign key dependencies
                def get_table_dependencies(table_name, source_host, source_user, source_pass):
                    """Get list of tables that need to be synced (table + its dependencies)"""
                    try:
                        dep_conn = mysql.connector.connect(
                            host=source_host,
                            port=3306,
                            user=source_user,
                            password=source_pass if source_pass else "",
                            database="offta",
                            connection_timeout=30
                        )
                        dep_cursor = dep_conn.cursor()
                        
                        # Get foreign key dependencies
                        dep_cursor.execute(f"""
                            SELECT DISTINCT REFERENCED_TABLE_NAME
                            FROM information_schema.KEY_COLUMN_USAGE
                            WHERE TABLE_SCHEMA = 'offta'
                            AND TABLE_NAME = '{table_name}'
                            AND REFERENCED_TABLE_NAME IS NOT NULL
                        """)
                        
                        dependencies = [row[0] for row in dep_cursor.fetchall()]
                        dep_cursor.close()
                        dep_conn.close()
                        
                        # Return dependencies first, then the table itself
                        return dependencies + [table_name]
                    except:
                        # If we can't get dependencies, just return the table
                        return [table_name]
                
                # Function to sync single table
                def sync_single_table(table_name, direction):
                    """Sync a single table (and its dependencies)"""
                    is_local_to_remote = (direction == "local_to_remote")
                    direction_text = "Local → Remote" if is_local_to_remote else "Remote → Local"
                    
                    # Switch to log tab
                    notebook.select(1)
                    log_status(f"\n{'='*60}", "info")
                    log_status(f"Syncing table '{table_name}' ({direction_text})...", "info")
                    status_label.config(text=f"Syncing {table_name}...", fg="#3498DB")
                    progress_bar.pack(pady=5)
                    progress_bar.start(10)
                    compare_win.update()
                    
                    temp_dir = tempfile.mkdtemp()
                    dump_file = os.path.join(temp_dir, f"sync_{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
                    
                    try:
                        # Configure source and destination
                        if is_local_to_remote:
                            source_host, source_user, source_pass = "localhost", "root", ""
                            dest_host, dest_user, dest_pass = "172.104.206.182", "seattlelisted_usr", "T@5z6^pl}"
                        else:
                            source_host, source_user, source_pass = "172.104.206.182", "seattlelisted_usr", "T@5z6^pl}"
                            dest_host, dest_user, dest_pass = "localhost", "root", ""
                        
                        # Get table dependencies
                        tables_to_sync = get_table_dependencies(table_name, source_host, source_user, source_pass)
                        
                        if len(tables_to_sync) > 1:
                            log_status(f"Dependencies detected: {', '.join(tables_to_sync[:-1])}", "info")
                            log_status(f"Will sync {len(tables_to_sync)} tables together", "info")
                        
                        # Dump table(s)
                        log_status(f"Dumping from {source_host}...", "info")
                        dump_cmd = [mysqldump_path, "-h", source_host, "-u", source_user]
                        if source_pass:
                            dump_cmd.append(f"-p{source_pass}")
                        dump_cmd.extend(["--databases", "offta", "--tables"] + tables_to_sync + 
                                       ["--single-transaction", "--quick", "--lock-tables=false",
                                        "--complete-insert"])
                        
                        with open(dump_file, "w", encoding="utf-8") as f:
                            result = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                        
                        if result.returncode != 0:
                            raise Exception(f"mysqldump failed: {result.stderr}")
                        
                        log_status(f"✓ Dump complete ({os.path.getsize(dump_file):,} bytes)", "ok")
                        
                        # Import table using Python mysql.connector (to avoid auth plugin issues)
                        log_status(f"Importing to {dest_host}...", "info")
                        
                        import_conn = mysql.connector.connect(
                            host=dest_host,
                            port=3306,
                            user=dest_user,
                            password=dest_pass if dest_pass else "",
                            database="offta",
                            connection_timeout=60
                        )
                        import_cursor = import_conn.cursor()
                        
                        # Disable foreign key checks to allow dropping tables with dependencies
                        import_cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                        
                        # Drop existing tables to ensure clean sync (in reverse order)
                        for tbl in reversed(tables_to_sync):
                            try:
                                import_cursor.execute(f"DROP TABLE IF EXISTS `{tbl}`")
                                log_status(f"Dropped existing table '{tbl}'", "info")
                            except:
                                pass
                        
                        # Read and execute SQL dump (use latin1 to handle binary data in BLOBs)
                        with open(dump_file, "r", encoding="latin1") as f:
                            sql_content = f.read()
                        
                        # Fix generated column issues - MySQL auto-calculates these
                        # 1. apartment_listings_price_changes: 'date' column
                        sql_content = sql_content.replace(
                            "INSERT INTO `apartment_listings_price_changes` (`id`, `apartment_listings_id`, `new_price`, `time`, `date`)",
                            "INSERT INTO `apartment_listings_price_changes` (`id`, `apartment_listings_id`, `new_price`, `time`)"
                        )
                        sql_content = re.sub(r",'(\d{4}-\d{2}-\d{2})'\)", r")", sql_content)
                        
                        # 2. queue_websites: 'hash_key' is GENERATED column - remove from CREATE TABLE and INSERT
                        # Remove the entire hash_key column definition from CREATE TABLE
                        sql_content = re.sub(
                            r",\s*`hash_key`[^,]*GENERATED[^,]*STORED",
                            "",
                            sql_content,
                            flags=re.IGNORECASE
                        )
                        # Also remove unique key constraint on hash_key
                        sql_content = re.sub(
                            r",\s*UNIQUE KEY `uq_queue_hash` \(`hash_key`\)",
                            "",
                            sql_content
                        )
                        # Remove hash_key from INSERT column list (appears after `processed_at`)
                        before_col_fix = sql_content
                        sql_content = re.sub(
                            r"(`processed_at`),\s*`hash_key`",
                            r"\1",
                            sql_content
                        )
                        if before_col_fix != sql_content:
                            log_status("→ Removed hash_key from INSERT column list", "info")
                        
                        # Remove hash_key value from VALUES - it's the 15th value (binary string between processed_at and run_interval_minutes)
                        # The value appears as: '2025-11-08 18:32:22','[binary_data]',4320
                        # We need to remove: ,'[binary_data]'
                        before_val_fix = sql_content
                        sql_content = re.sub(
                            r"(\`processed_at\`\) VALUES \([^)]*'[\d\-: ]+')\s*,\s*'[^']*'\s*,(\s*\d+\s*,)",
                            r"\1,\2",
                            sql_content
                        )
                        if before_val_fix != sql_content:
                            log_status("→ Removed hash_key from INSERT VALUES", "info")
                        
                        # Count statement types
                        create_count = sql_content.upper().count('CREATE TABLE')
                        insert_count = sql_content.upper().count('INSERT INTO')
                        
                        # Check if dump actually has data
                        if insert_count == 0:
                            log_status(f"⚠ WARNING: Dump has no INSERT statements! Source table may be empty.", "warn")
                        
                        log_status(f"Dump contains: {create_count} CREATE, {insert_count} INSERT statements", "info")
                        
                        # Import using Python mysql.connector (avoids auth plugin issues with mysql.exe)
                        log_status(f"Importing SQL statements...", "info")
                        
                        # Execute statements
                        import_cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                        import_cursor.execute("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO'")
                        
                        # Split by semicolons that are followed by newline (actual statement terminators)
                        # This handles multi-line INSERT statements properly
                        statements = re.split(r';\s*\n', sql_content)
                        
                        executed = 0
                        inserts_executed = 0
                        failed_inserts = 0
                        for stmt in statements:
                            stmt = stmt.strip()
                            if not stmt or stmt.startswith('--') or stmt.startswith('/*'):
                                continue
                            
                            # Skip SET and USE statements from mysqldump
                            stmt_upper = stmt.upper()
                            if stmt_upper.startswith('USE ') or stmt_upper.startswith('SET '):
                                continue
                            
                            is_insert = 'INSERT INTO' in stmt_upper
                            try:
                                import_cursor.execute(stmt)
                                executed += 1
                                if is_insert:
                                    inserts_executed += 1
                                    # Log which table was inserted
                                    match = re.search(r'INSERT INTO [`\"]?(\w+)', stmt_upper)
                                    if match:
                                        log_status(f"  → Inserted data into {match.group(1)}", "info")
                            except Exception as e:
                                error_msg = str(e)
                                # Check if it's an INSERT that failed
                                if is_insert:
                                    failed_inserts += 1
                                    log_status(f"⚠ INSERT failed: {error_msg}", "warn")
                                    # Show preview of failed statement
                                    preview = stmt[:300].replace('\n', ' ')
                                    log_status(f"  Statement: {preview}...", "warn")
                                elif 'generated column' not in error_msg.lower():
                                    log_status(f"⚠ Error: {error_msg[:150]}", "warn")
                        
                        import_cursor.execute("SET FOREIGN_KEY_CHECKS=1")
                        import_conn.commit()
                        import_cursor.close()
                        import_conn.close()
                        
                        if failed_inserts > 0:
                            log_status(f"⚠ {failed_inserts} INSERT statements failed!", "warn")
                        
                        log_status(f"✓ Executed {executed} statements ({inserts_executed} successful inserts)", "info")
                        
                        # Verify import by counting rows for each synced table
                        verify_conn = mysql.connector.connect(
                            host=dest_host,
                            port=3306,
                            user=dest_user,
                            password=dest_pass if dest_pass else "",
                            database="offta",
                            connection_timeout=30
                        )
                        verify_cursor = verify_conn.cursor()
                        
                        # Check all synced tables
                        for tbl in tables_to_sync:
                            verify_cursor.execute(f"SELECT COUNT(*) FROM `{tbl}`")
                            tbl_count = verify_cursor.fetchone()[0]
                            log_status(f"  '{tbl}': {tbl_count:,} rows", "info")
                        
                        verify_cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                        row_count = verify_cursor.fetchone()[0]
                        verify_cursor.close()
                        verify_conn.close()
                        log_status(f"✓ Verified: '{table_name}' now has {row_count:,} rows", "ok")
                        
                        # Only report success if INSERTs actually succeeded
                        if failed_inserts > 0:
                            log_status(f"✗ Sync completed with {failed_inserts} failures", "err")
                            status_label.config(text=f"✗ {table_name} sync failed", fg="#E74C3C")
                            log_to_file(f"[Sync] ✗ Failed to sync table '{table_name}' {direction_text} - {failed_inserts} INSERT failures")
                        elif len(tables_to_sync) > 1:
                            log_status(f"✓ Synced {len(tables_to_sync)} tables: {', '.join(tables_to_sync)}", "ok")
                            status_label.config(text=f"✓ {table_name} synced", fg="#27AE60")
                            log_to_file(f"[Sync] ✓ Synced table '{table_name}' {direction_text}")
                        else:
                            log_status(f"✓ Table '{table_name}' synced successfully!", "ok")
                            status_label.config(text=f"✓ {table_name} synced", fg="#27AE60")
                            log_to_file(f"[Sync] ✓ Synced table '{table_name}' {direction_text}")
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "caching_sha2_password" in error_msg:
                            error_msg = "Authentication plugin error"
                        log_status(f"✗ Failed: {error_msg}", "err")
                        status_label.config(text=f"✗ Sync failed", fg="#E74C3C")
                        log_to_file(f"[Sync] ✗ Failed to sync '{table_name}': {e}")
                    finally:
                        progress_bar.stop()
                        progress_bar.pack_forget()
                        try:
                            if os.path.exists(dump_file):
                                os.remove(dump_file)
                            os.rmdir(temp_dir)
                        except:
                            pass
                
                # Data rows
                for idx, diff_data in enumerate(table_diffs):
                    table_name = diff_data['table']
                    local_val = diff_data['local']
                    remote_val = diff_data['remote']
                    diff_val = diff_data['diff']
                    
                    # Format display strings
                    local_display = f"{local_val:,}" if isinstance(local_val, int) else str(local_val)
                    remote_display = f"{remote_val:,}" if isinstance(remote_val, int) else str(remote_val)
                    
                    if diff_val == '?':
                        diff_str = "?"
                        diff_color = "#95A5A6"
                    elif diff_val == 0:
                        diff_str = "No change"
                        diff_color = "#95A5A6"
                    elif diff_val > 0:
                        diff_str = f"+{diff_val:,}"
                        diff_color = "#27AE60"
                    else:
                        diff_str = f"{diff_val:,}"
                        diff_color = "#E74C3C"
                    
                    # Alternate row colors
                    row_bg = "#ECF0F1" if idx % 2 == 0 else "white"
                    
                    row_frame = tk.Frame(scrollable_frame, bg=row_bg, relief="flat")
                    row_frame.pack(fill="x", pady=1)
                    
                    tk.Label(row_frame, text=table_name, bg=row_bg, fg="#2C3E50",
                            font=("Segoe UI", 9), width=20, anchor="w").pack(side="left", padx=5, pady=3)
                    tk.Label(row_frame, text=local_display, 
                            bg=row_bg, fg="#2C3E50", font=("Segoe UI", 9), width=10, anchor="center").pack(side="left", padx=5, pady=3)
                    tk.Label(row_frame, text=remote_display, 
                            bg=row_bg, fg="#2C3E50", font=("Segoe UI", 9), width=10, anchor="center").pack(side="left", padx=5, pady=3)
                    tk.Label(row_frame, text=diff_str, bg=row_bg, fg=diff_color,
                            font=("Segoe UI", 9, "bold"), width=15, anchor="center").pack(side="left", padx=5, pady=3)
                    
                    # Action buttons
                    btn_frame = tk.Frame(row_frame, bg=row_bg)
                    btn_frame.pack(side="left", padx=5)
                    
                    # Only show L→R button if table exists locally
                    if isinstance(local_val, int) and local_val > 0:
                        tk.Button(btn_frame, text="⬆️", bg="#27AE60", fg="white",
                                font=("Segoe UI", 8, "bold"), width=3, cursor="hand2",
                                command=lambda t=table_name: sync_single_table(t, "local_to_remote")
                        ).pack(side="left", padx=2)
                    else:
                        tk.Label(btn_frame, text="  ", bg=row_bg, width=3).pack(side="left", padx=2)
                    
                    # Only show R→L button if table exists remotely
                    if isinstance(remote_val, int) and remote_val > 0:
                        tk.Button(btn_frame, text="⬇️", bg="#3498DB", fg="white",
                                font=("Segoe UI", 8, "bold"), width=3, cursor="hand2",
                                command=lambda t=table_name: sync_single_table(t, "remote_to_local")
                        ).pack(side="left", padx=2)
                    else:
                        tk.Label(btn_frame, text="  ", bg=row_bg, width=3).pack(side="left", padx=2)
                
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                # Tab 2: Sync Log
                log_tab = tk.Frame(notebook, bg="white")
                notebook.add(log_tab, text="📋 Sync Log")
                
                log_text = tk.Text(
                    log_tab,
                    bg="#F8F9FA",
                    fg="#2C3E50",
                    font=("Consolas", 9),
                    relief="flat",
                    wrap="word"
                )
                log_scrollbar = ttk.Scrollbar(log_tab, orient="vertical", command=log_text.yview)
                log_text.configure(yscrollcommand=log_scrollbar.set)
                log_text.pack(side="left", fill="both", expand=True)
                log_scrollbar.pack(side="right", fill="y")
                
                def log_status(message, level="info"):
                    """Add message to status log"""
                    colors = {"info": "#2C3E50", "ok": "#27AE60", "err": "#E74C3C", "warn": "#E67E22"}
                    log_text.insert("end", f"{message}\n", level)
                    log_text.tag_config(level, foreground=colors.get(level, "#2C3E50"))
                    log_text.see("end")
                    compare_win.update()
                
                # Log initial info
                log_status(f"Database comparison complete", "info")
                log_status(f"Found {len(table_diffs)} tables", "info")
                tables_with_diff = [d for d in table_diffs if d['diff'] != 0 and d['diff'] != '?']
                if tables_with_diff:
                    log_status(f"{len(tables_with_diff)} tables have differences", "warn")
                    for d in tables_with_diff[:5]:  # Show first 5
                        diff_val = d['diff']
                        if diff_val > 0:
                            log_status(f"  {d['table']}: +{diff_val:,} rows", "ok")
                        else:
                            log_status(f"  {d['table']}: {diff_val:,} rows", "err")
                    if len(tables_with_diff) > 5:
                        log_status(f"  ... and {len(tables_with_diff) - 5} more", "info")
                else:
                    log_status("All tables are synchronized", "ok")
                
                # Sync functions that update status
                syncing = [False]  # Track if sync in progress
                
                def perform_sync(direction):
                    """Perform the actual sync with status updates"""
                    if syncing[0]:
                        return
                    
                    syncing[0] = True
                    is_local_to_remote = (direction == "local_to_remote")
                    direction_text = "Local → Remote" if is_local_to_remote else "Remote → Local"
                    
                    # Switch to log tab and update UI
                    notebook.select(1)  # Switch to log tab (index 1)
                    status_label.config(text=f"Syncing ({direction_text})...", fg="#3498DB")
                    progress_bar.pack(pady=5)
                    progress_bar.start(10)
                    compare_win.update()
                    
                    # Create temp directory for SQL dump
                    temp_dir = tempfile.mkdtemp()
                    dump_file = os.path.join(temp_dir, f"sync_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
                    
                    try:
                        log_status(f"\n{'='*60}", "info")
                        log_status(f"Starting {direction_text} sync...", "info")
                        
                        # Configure source and destination
                        if is_local_to_remote:
                            source_host, source_user, source_pass = "localhost", "root", ""
                            dest_host, dest_user, dest_pass = "172.104.206.182", "seattlelisted_usr", "T@5z6^pl}"
                            tables_to_sync = [d['table'] for d in table_diffs if isinstance(d['local'], int) and d['local'] > 0]
                        else:
                            source_host, source_user, source_pass = "172.104.206.182", "seattlelisted_usr", "T@5z6^pl}"
                            dest_host, dest_user, dest_pass = "localhost", "root", ""
                            tables_to_sync = [d['table'] for d in table_diffs if isinstance(d['remote'], int) and d['remote'] > 0]
                        
                        log_status(f"Dumping {len(tables_to_sync)} tables from {source_host}...", "info")
                        status_label.config(text=f"Dumping {len(tables_to_sync)} tables...")
                        compare_win.update()
                        
                        # Build dump command
                        dump_cmd = [mysqldump_path, "-h", source_host, "-u", source_user]
                        if source_pass:
                            dump_cmd.append(f"-p{source_pass}")
                        dump_cmd.extend(["--databases", "offta", "--tables"] + tables_to_sync + 
                                      ["--single-transaction", "--quick", "--lock-tables=false",
                                       "--complete-insert", "--add-drop-table"])
                        
                        with open(dump_file, "w", encoding="utf-8") as f:
                            result = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
                        
                        if result.returncode != 0:
                            raise Exception(f"mysqldump failed: {result.stderr}")
                        
                        log_status(f"✓ Dump complete ({os.path.getsize(dump_file):,} bytes)", "ok")
                        
                        # Import to destination using Python mysql.connector
                        log_status(f"Importing to {dest_host}...", "info")
                        status_label.config(text=f"Importing to {dest_host}...")
                        compare_win.update()
                        
                        import_conn = mysql.connector.connect(
                            host=dest_host,
                            port=3306,
                            user=dest_user,
                            password=dest_pass if dest_pass else "",
                            database="offta",
                            connection_timeout=60
                        )
                        import_cursor = import_conn.cursor()
                        
                        # Disable foreign key checks and drop existing tables to ensure clean sync
                        log_status(f"Dropping {len(tables_to_sync)} existing tables...", "info")
                        import_cursor.execute("SET FOREIGN_KEY_CHECKS=0")
                        import_cursor.execute("SET SQL_MODE='NO_AUTO_VALUE_ON_ZERO'")
                        
                        dropped_count = 0
                        for tbl in tables_to_sync:
                            try:
                                # Force drop without IF EXISTS to ensure it actually happens
                                import_cursor.execute(f"DROP TABLE `{tbl}`")
                                dropped_count += 1
                                log_to_file(f"[Sync] ✓ Dropped table: {tbl}")
                            except Exception as drop_err:
                                # Table doesn't exist - that's fine
                                if "unknown table" in str(drop_err).lower() or "doesn't exist" in str(drop_err).lower():
                                    log_to_file(f"[Sync] Table {tbl} doesn't exist (ok)")
                                else:
                                    log_to_file(f"[Sync] ✗ Failed to drop table {tbl}: {drop_err}")
                        import_conn.commit()
                        log_status(f"✓ Dropped {dropped_count}/{len(tables_to_sync)} tables", "ok")
                        
                        # Verify tables were dropped
                        import_cursor.execute("SHOW TABLES")
                        remaining_tables = [row[0] for row in import_cursor.fetchall() if row[0] in tables_to_sync]
                        if remaining_tables:
                            log_status(f"⚠ Warning: {len(remaining_tables)} tables still exist after drop", "warn")
                            log_to_file(f"[Sync] Tables still present: {remaining_tables}")
                        else:
                            log_status(f"✓ All {len(tables_to_sync)} tables dropped successfully", "ok")
                        
                        # Read and execute SQL dump (use latin1 to handle binary data in BLOBs)
                        with open(dump_file, "r", encoding="latin1") as f:
                            sql_content = f.read()
                        
                        # Fix generated column issues - MySQL auto-calculates these
                        # 1. apartment_listings_price_changes: 'date' column
                        sql_content = sql_content.replace(
                            "INSERT INTO `apartment_listings_price_changes` (`id`, `apartment_listings_id`, `new_price`, `time`, `date`)",
                            "INSERT INTO `apartment_listings_price_changes` (`id`, `apartment_listings_id`, `new_price`, `time`)"
                        )
                        sql_content = re.sub(r",'(\d{4}-\d{2}-\d{2})'\)", r")", sql_content)
                        
                        # 2. queue_websites: 'hash_key' is GENERATED column - remove from CREATE TABLE and INSERT
                        # Remove the entire hash_key column definition from CREATE TABLE
                        sql_content = re.sub(
                            r",\s*`hash_key`[^,]*GENERATED[^,]*STORED",
                            "",
                            sql_content,
                            flags=re.IGNORECASE
                        )
                        # Also remove unique key constraint on hash_key
                        sql_content = re.sub(
                            r",\s*UNIQUE KEY `uq_queue_hash` \(`hash_key`\)",
                            "",
                            sql_content
                        )
                        # Remove hash_key from INSERT column list (appears after `processed_at`)
                        sql_content = re.sub(
                            r"(`processed_at`),\s*`hash_key`",
                            r"\1",
                            sql_content
                        )
                        # Remove hash_key value from VALUES - it's the 15th value (binary string between processed_at and run_interval_minutes)
                        # The value appears as: '2025-11-08 18:32:22','[binary_data]',4320
                        # We need to remove: ,'[binary_data]'
                        sql_content = re.sub(
                            r"(\`processed_at\`\) VALUES \([^)]*'[\d\-: ]+')\s*,\s*'[^']*'\s*,(\s*\d+\s*,)",
                            r"\1,\2",
                            sql_content
                        )
                        
                        # Count statement types
                        create_count = sql_content.upper().count('CREATE TABLE')
                        insert_count = sql_content.upper().count('INSERT INTO')
                        
                        # Check if dump actually has data
                        if insert_count == 0:
                            log_status(f"⚠ WARNING: Dump has no INSERT statements! Source tables may be empty.", "warn")
                        
                        log_status(f"Dump contains: {create_count} CREATE, {insert_count} INSERT statements", "info")
                        
                        # Import using Python mysql.connector (avoids auth plugin issues with mysql.exe)
                        log_status(f"Importing SQL statements...", "info")
                        
                        # Foreign key checks and SQL mode already set above before dropping tables
                        
                        # Split by semicolons that are followed by newline (actual statement terminators)
                        # This handles multi-line INSERT statements properly
                        statements = re.split(r';\s*\n', sql_content)
                        
                        executed = 0
                        inserts_executed = 0
                        for stmt in statements:
                            stmt = stmt.strip()
                            if not stmt or stmt.startswith('--') or stmt.startswith('/*'):
                                continue
                            
                            # Skip SET and USE statements from mysqldump
                            stmt_upper = stmt.upper()
                            if stmt_upper.startswith('USE ') or stmt_upper.startswith('SET '):
                                continue
                            
                            try:
                                import_cursor.execute(stmt)
                                executed += 1
                                if 'INSERT INTO' in stmt_upper:
                                    inserts_executed += 1
                            except Exception as e:
                                error_msg = str(e)
                                if 'generated column' not in error_msg.lower():
                                    log_status(f"⚠ Error: {error_msg[:150]}", "warn")
                        
                        import_cursor.execute("SET FOREIGN_KEY_CHECKS=1")
                        import_conn.commit()
                        import_cursor.close()
                        import_conn.close()
                        
                        log_status(f"✓ Executed {executed} statements ({inserts_executed} inserts)", "info")
                        log_status(f"✓ Successfully synced {len(tables_to_sync)} tables!", "ok")
                        status_label.config(text=f"✓ Sync complete! ({len(tables_to_sync)} tables)", fg="#27AE60")
                        
                    except Exception as e:
                        error_msg = str(e)
                        if "caching_sha2_password" in error_msg:
                            error_msg = "Authentication plugin error. Try updating MySQL credentials."
                        log_status(f"✗ Sync failed: {error_msg}", "err")
                        status_label.config(text=f"✗ Sync failed", fg="#E74C3C")
                        log_to_file(f"[Sync] ✗ Sync failed: {e}")
                        
                    finally:
                        progress_bar.stop()
                        progress_bar.pack_forget()
                        syncing[0] = False
                        try:
                            if os.path.exists(dump_file):
                                os.remove(dump_file)
                            os.rmdir(temp_dir)
                        except:
                            pass
                
                # Button commands
                def on_local_to_remote():
                    perform_sync("local_to_remote")
                
                def on_remote_to_local():
                    perform_sync("remote_to_local")
                
                def refresh_tables():
                    """Refresh table data"""
                    status_label.config(text="Refreshing table data...", fg="#3498DB")
                    progress_bar.pack(pady=5)
                    progress_bar.start(10)
                    compare_win.update()
                    
                    try:
                        log_status("\n" + "="*60, "info")
                        log_status("Refreshing table data...", "info")
                        
                        # Re-fetch table data
                        local_conn = mysql.connector.connect(
                            host="localhost",
                            user="root",
                            password="",
                            database="offta"
                        )
                        local_cursor = local_conn.cursor()
                        
                        remote_conn = mysql.connector.connect(
                            host="172.104.206.182",
                            port=3306,
                            user="seattlelisted_usr",
                            password="T@5z6^pl}",
                            database="offta",
                            connection_timeout=30
                        )
                        remote_cursor = remote_conn.cursor()
                        
                        # Get tables
                        local_cursor.execute("SHOW TABLES")
                        local_tables = {row[0] for row in local_cursor.fetchall()}
                        
                        remote_cursor.execute("SHOW TABLES")
                        remote_tables = {row[0] for row in remote_cursor.fetchall()}
                        
                        all_tables = sorted(local_tables | remote_tables)
                        
                        # Get row counts
                        new_table_diffs = []
                        for table in all_tables:
                            local_count = "N/A"
                            remote_count = "N/A"
                            
                            if table in local_tables:
                                try:
                                    local_cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                                    local_count = local_cursor.fetchone()[0]
                                except:
                                    local_count = "?"
                            
                            if table in remote_tables:
                                try:
                                    remote_cursor.execute(f"SELECT COUNT(*) FROM `{table}`")
                                    remote_count = remote_cursor.fetchone()[0]
                                except:
                                    remote_count = "?"
                            
                            # Calculate diff
                            if isinstance(local_count, int) and isinstance(remote_count, int):
                                diff = local_count - remote_count
                            else:
                                diff = "?"
                            
                            new_table_diffs.append({
                                'table': table,
                                'local': local_count,
                                'remote': remote_count,
                                'diff': diff
                            })
                        
                        local_cursor.close()
                        remote_cursor.close()
                        
                        # Clear and rebuild table rows
                        for widget in scrollable_frame.winfo_children():
                            if widget != header_frame:
                                widget.destroy()
                        
                        # Rebuild data rows
                        for idx, diff_data in enumerate(new_table_diffs):
                            table_name = diff_data['table']
                            local_val = diff_data['local']
                            remote_val = diff_data['remote']
                            diff_val = diff_data['diff']
                            
                            # Format display strings
                            local_display = f"{local_val:,}" if isinstance(local_val, int) else str(local_val)
                            remote_display = f"{remote_val:,}" if isinstance(remote_val, int) else str(remote_val)
                            
                            if diff_val == '?':
                                diff_str = "?"
                                diff_color = "#95A5A6"
                            elif diff_val == 0:
                                diff_str = "No change"
                                diff_color = "#95A5A6"
                            elif diff_val > 0:
                                diff_str = f"+{diff_val:,}"
                                diff_color = "#27AE60"
                            else:
                                diff_str = f"{diff_val:,}"
                                diff_color = "#E74C3C"
                            
                            row_bg = "#ECF0F1" if idx % 2 == 0 else "white"
                            row_frame = tk.Frame(scrollable_frame, bg=row_bg, relief="flat")
                            row_frame.pack(fill="x", pady=1)
                            
                            tk.Label(row_frame, text=table_name, bg=row_bg, fg="#2C3E50",
                                    font=("Segoe UI", 9), width=20, anchor="w").pack(side="left", padx=5, pady=3)
                            tk.Label(row_frame, text=local_display, 
                                    bg=row_bg, fg="#2C3E50", font=("Segoe UI", 9), width=10, anchor="center").pack(side="left", padx=5, pady=3)
                            tk.Label(row_frame, text=remote_display, 
                                    bg=row_bg, fg="#2C3E50", font=("Segoe UI", 9), width=10, anchor="center").pack(side="left", padx=5, pady=3)
                            tk.Label(row_frame, text=diff_str, bg=row_bg, fg=diff_color,
                                    font=("Segoe UI", 9, "bold"), width=15, anchor="center").pack(side="left", padx=5, pady=3)
                            
                            btn_frame = tk.Frame(row_frame, bg=row_bg)
                            btn_frame.pack(side="left", padx=5)
                            
                            if isinstance(local_val, int) and local_val > 0:
                                tk.Button(btn_frame, text="⬆️", bg="#27AE60", fg="white",
                                        font=("Segoe UI", 8, "bold"), width=3, cursor="hand2",
                                        command=lambda t=table_name: sync_single_table(t, "local_to_remote")
                                ).pack(side="left", padx=2)
                            else:
                                tk.Label(btn_frame, text="  ", bg=row_bg, width=3).pack(side="left", padx=2)
                            
                            if isinstance(remote_val, int) and remote_val > 0:
                                tk.Button(btn_frame, text="⬇️", bg="#3498DB", fg="white",
                                        font=("Segoe UI", 8, "bold"), width=3, cursor="hand2",
                                        command=lambda t=table_name: sync_single_table(t, "remote_to_local")
                                ).pack(side="left", padx=2)
                            else:
                                tk.Label(btn_frame, text="  ", bg=row_bg, width=3).pack(side="left", padx=2)
                        
                        # Clean up connections
                        local_cursor.close()
                        local_conn.close()
                        remote_cursor.close()
                        remote_conn.close()
                        
                        log_status(f"✓ Refreshed {len(new_table_diffs)} tables", "ok")
                        status_label.config(text="✓ Tables refreshed", fg="#27AE60")
                        
                    except Exception as e:
                        log_status(f"✗ Refresh failed: {e}", "err")
                        status_label.config(text="✗ Refresh failed", fg="#E74C3C")
                    finally:
                        # Clean up connections if they exist
                        try:
                            local_cursor.close()
                            local_conn.close()
                        except:
                            pass
                        try:
                            remote_cursor.close()
                            remote_conn.close()
                        except:
                            pass
                        progress_bar.stop()
                        progress_bar.pack_forget()
                
                # Create buttons
                tk.Button(
                    button_frame,
                    text="⬆️ Sync Local → Remote",
                    command=on_local_to_remote,
                    bg="#27AE60",
                    fg="white",
                    font=("Segoe UI", 11, "bold"),
                    padx=25,
                    pady=12,
                    cursor="hand2"
                ).pack(side="left", padx=5)
                
                tk.Button(
                    button_frame,
                    text="⬇️ Sync Remote → Local",
                    command=on_remote_to_local,
                    bg="#3498DB",
                    fg="white",
                    font=("Segoe UI", 11, "bold"),
                    padx=25,
                    pady=12,
                    cursor="hand2"
                ).pack(side="left", padx=5)
                
                tk.Button(
                    button_frame,
                    text="🔄 Refresh",
                    command=refresh_tables,
                    bg="#F39C12",
                    fg="white",
                    font=("Segoe UI", 11, "bold"),
                    padx=25,
                    pady=12,
                    cursor="hand2"
                ).pack(side="left", padx=5)
                
                tk.Button(
                    button_frame,
                    text="✗ Close",
                    command=compare_win.destroy,
                    bg="#95A5A6",
                    fg="white",
                    font=("Segoe UI", 11, "bold"),
                    padx=25,
                    pady=12,
                    cursor="hand2"
                ).pack(side="left", padx=5)
                

                
            except Exception as ex:
                log_to_file(f"[Sync] Sync button handler error: {ex}")
                log_exception("Sync button handler error")
                print(f"[Sync] Sync button handler error: {ex}")
        sync_btn.bind("<Button-1>", _on_sync_btn)
        
        # Last 3 log messages at the bottom of the window
        last_box = tk.Frame(body, bg=bg)
        last_box.pack(fill="x", side="bottom", pady=(8, 0))
        
        self._last_logs = []  # Store last 3 log labels
        for i in range(3):
            log_label = tk.Label(last_box, text="", fg=muted, bg=bg, font=("Consolas", 9), anchor="w")
            log_label.pack(side="top", anchor="w", fill="x")
            self._last_logs.append(log_label)
        
        # Set initial message in first log
        self._last_logs[0].config(text="Ready.")
        
        # For backward compatibility, keep self._last pointing to the most recent (bottom) log
        self._last = self._last_logs[-1]
        
        # Context menu for copying the last message
        self._last_menu = tk.Menu(self._last, tearoff=0)
        def _copy_last_to_clipboard(_e=None):
            try:
                txt = self._last.cget("text") or ""
                self._root.clipboard_clear()
                self._root.clipboard_append(txt)
                # Keep clipboard data after app closes
                try:
                    self._root.update()
                except Exception:
                    pass
            except Exception:
                pass
        self._last_menu.add_command(label="Copy", command=_copy_last_to_clipboard)

        def _on_last_right_click(e):
            try:
                self._last_menu.tk_popup(e.x_root, e.y_root)
            finally:
                try: self._last_menu.grab_release()
                except Exception: pass

        # Bind right-click for context menu and double-click to quick-copy
        self._last.bind("<Button-3>", _on_last_right_click)
        self._last.bind("<Double-Button-1>", _copy_last_to_clipboard)

    def _start_job_step(self, job_id, table, step):
        """Start a specific step for a job - called from UI thread"""
        try:
            import requests
            log_to_file(f"[Queue] ========== START JOB STEP ==========")
            log_to_file(f"[Queue] Job ID: {job_id}")
            log_to_file(f"[Queue] Table: {table}")
            log_to_file(f"[Queue] Step: {step}")
            
            # Print to console for visibility
            print(f"\n{'='*80}")
            print(f"[STEP {step.upper()}] Starting for job {job_id} in table {table}")
            print(f"{'='*80}\n")
            
            # Try to call API to update step status (optional - don't block if it fails)
            try:
                    api_url = php_url("queue_step_api.php")
                    payload = {
                        'table': table,
                        'id': job_id,
                        'step': step,
                        'status': 'running',
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    }
                
                    response = requests.post(api_url, json=payload, timeout=5)
                    if response.status_code == 200:
                        log_to_file(f"[Queue] Step {step} status updated in API")
                    else:
                        log_to_file(f"[Queue] API returned status {response.status_code}, continuing anyway...")
            except Exception as api_err:
                log_to_file(f"[Queue] API call failed (continuing anyway): {api_err}")
            
            # Execute the actual step regardless of API status
            log_to_file(f"[Queue] Executing step {step}...")
            print(f"[STEP {step.upper()}] About to execute...")
            self._execute_step(job_id, table, step)
            
        except Exception as e:
            log_to_file(f"[Queue] Failed to start step {step} for job {job_id}: {e}")
            log_exception("Start job step error")
            
            def _show_error():
                self._queue_status_label.config(text=f"Failed: {str(e)[:50]}")
            
            self._root.after(0, _show_error)
    
    def _show_json_summary(self):
        """Show summary of all JSON files extracted today"""
        try:
            log_to_file(f"[Queue] Opening JSON summary...")
            
            # Create summary window
            summary_window = tk.Toplevel(self._root)
            summary_window.title("📊 JSON Extraction Summary")
            summary_window.geometry("900x700")
            summary_window.configure(bg="#2C3E50")
            
            # Header
            header_frame = tk.Frame(summary_window, bg="#34495E")
            header_frame.pack(fill="x", padx=0, pady=0)
            
            today_str = datetime.now().strftime("%Y-%m-%d")
            tk.Label(header_frame, text=f"📊 JSON Files Extracted on {today_str}", 
                     bg="#34495E", fg="#ECF0F1", font=("Segoe UI", 14, "bold")).pack(pady=15)
            
            # Main content with scrollbar
            main_frame = tk.Frame(summary_window, bg="#2C3E50")
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            from tkinter import scrolledtext
            text_widget = scrolledtext.ScrolledText(
                main_frame, 
                bg="#34495E", 
                fg="#ECF0F1", 
                insertbackground="#ECF0F1",
                font=("Consolas", 9),
                wrap="word"
            )
            text_widget.pack(fill="both", expand=True)
            
            # Find all JSON files from today
            date_str = datetime.now().strftime("%Y-%m-%d")
            html_dir = BASE_DIR / date_str
            
            if not html_dir.exists():
                text_widget.insert("1.0", f"⚠️ No captures folder found for today ({date_str})")
                return
            
            json_files = list(html_dir.glob("*.json"))
            
            if not json_files:
                text_widget.insert("1.0", f"⚠️ No JSON files found for today ({date_str})")
                return
            
            # Build summary
            summary_lines = []
            summary_lines.append("="*80)
            summary_lines.append(f"📊 JSON EXTRACTION SUMMARY - {today_str}")
            summary_lines.append("="*80)
            summary_lines.append(f"📁 Location: {html_dir}")
            summary_lines.append(f"📄 Total JSON files: {len(json_files)}")
            summary_lines.append("="*80)
            summary_lines.append("")
            
            # Analyze each JSON file
            from collections import defaultdict
            
            for idx, json_file in enumerate(sorted(json_files), 1):
                try:
                    summary_lines.append(f"\n{'─'*80}")
                    summary_lines.append(f"📄 File #{idx}: {json_file.name}")
                    summary_lines.append(f"{'─'*80}")
                    
                    # Get file info
                    file_size = json_file.stat().st_size
                    modified_time = datetime.fromtimestamp(json_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    summary_lines.append(f"📊 Size: {file_size:,} bytes")
                    summary_lines.append(f"🕐 Modified: {modified_time}")
                    
                    # Load JSON
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Handle different JSON structures
                    if isinstance(data, list):
                        listings = data
                    elif isinstance(data, dict):
                        if 'data' in data and isinstance(data['data'], list):
                            listings = data['data']
                        elif 'listings' in data and isinstance(data['listings'], list):
                            listings = data['listings']
                        else:
                            listings = [data]
                    else:
                        summary_lines.append(f"⚠️ Unexpected JSON type: {type(data)}")
                        continue
                    
                    total_entries = len(listings)
                    summary_lines.append(f"📋 Total Entries: {total_entries}")
                    summary_lines.append("")
                    
                    if total_entries == 0:
                        summary_lines.append("⚠️ No entries found")
                        continue
                    
                    # Analyze fields
                    field_stats = defaultdict(lambda: {
                        'count': 0,
                        'non_empty': 0,
                        'sample_values': []
                    })
                    
                    for entry in listings:
                        if not isinstance(entry, dict):
                            continue
                        
                        for field_name, field_value in entry.items():
                            stats = field_stats[field_name]
                            stats['count'] += 1
                            
                            # Check if non-empty
                            if field_value is not None and field_value != "" and field_value != []:
                                stats['non_empty'] += 1
                            
                            # Collect sample values (first 3)
                            if len(stats['sample_values']) < 3 and field_value:
                                value_str = str(field_value)[:80]
                                if value_str not in stats['sample_values']:
                                    stats['sample_values'].append(value_str)
                    
                    # Display field statistics
                    summary_lines.append("🔑 FIELD SUMMARY:")
                    summary_lines.append("")
                    
                    for field_name in sorted(field_stats.keys()):
                        stats = field_stats[field_name]
                        pct = (stats['non_empty'] * 100 // stats['count']) if stats['count'] > 0 else 0
                        summary_lines.append(f"  📌 {field_name}:")
                        summary_lines.append(f"     Total: {stats['count']}/{total_entries} | Non-empty: {stats['non_empty']} ({pct}%)")
                        
                        if stats['sample_values']:
                            summary_lines.append(f"     Samples:")
                            for i, sample in enumerate(stats['sample_values'], 1):
                                summary_lines.append(f"       {i}. {sample}")
                        summary_lines.append("")
                    
                except json.JSONDecodeError as je:
                    summary_lines.append(f"❌ JSON Parse Error: {je}")
                except Exception as e:
                    summary_lines.append(f"❌ Error analyzing file: {e}")
            
            # Final summary
            summary_lines.append("\n" + "="*80)
            summary_lines.append(f"✅ Summary complete - Analyzed {len(json_files)} JSON file(s)")
            summary_lines.append("="*80)
            
            # Display summary
            text_widget.insert("1.0", "\n".join(summary_lines))
            
            # Button frame
            btn_frame = tk.Frame(summary_window, bg="#2C3E50")
            btn_frame.pack(fill="x", padx=10, pady=10)
            
            tk.Button(btn_frame, text="🔄 Refresh", command=lambda: self._refresh_json_summary(summary_window),
                     bg="#3498DB", fg="#fff", font=("Segoe UI", 10, "bold"), padx=20, pady=8).pack(side="left", padx=5)
            tk.Button(btn_frame, text="✖ Close", command=summary_window.destroy,
                     bg="#E74C3C", fg="#fff", font=("Segoe UI", 10, "bold"), padx=20, pady=8).pack(side="left", padx=5)
            
        except Exception as e:
            log_to_file(f"[Queue] Error showing JSON summary: {e}")
            log_exception("JSON summary error")
            if hasattr(self, '_queue_status_label'):
                self._queue_status_label.config(text=f"✗ Summary failed: {str(e)[:40]}")
    
    def _refresh_json_summary(self, window):
        """Refresh the JSON summary window"""
        window.destroy()
        self._show_json_summary()
    
    def _show_json_summary_for_job(self, job_id, table):
        """Show JSON summary for a specific job's JSON file"""
        try:
            log_to_file(f"[Queue] Opening JSON summary for job {job_id}...")
            
            # Determine prefix based on table
            original_table = str(current_table).lower()
            prefix = original_table
            if original_table in ("queue_websites", "listing_websites", "websites"):
                prefix = "networks"
            else:
                if "_" in original_table:
                    prefix = original_table.split("_")[-1]
            
            # Find JSON file for this job
            date_str = datetime.now().strftime("%Y-%m-%d")
            html_dir = BASE_DIR / date_str
            json_file = html_dir / f"{prefix}_{job_id}.json"
            
            # If not found today, search other dates
            if not json_file.exists():
                import glob
                pattern = str(BASE_DIR / "*" / f"{prefix}_{job_id}.json")
                matching_files = glob.glob(pattern)
                if matching_files:
                    json_file = Path(max(matching_files, key=lambda p: os.path.getmtime(p)))
                else:
                    self._queue_status_label.config(text=f"❌ No JSON file found for job {job_id}")
                    return
            
            log_to_file(f"[Queue] Found JSON file: {json_file}")
            
            # Create summary window
            summary_window = tk.Toplevel(self._root)
            summary_window.title(f"📊 JSON Summary - Job {job_id}")
            summary_window.geometry("900x700")
            summary_window.configure(bg="#2C3E50")
            
            # Header
            header_frame = tk.Frame(summary_window, bg="#34495E")
            header_frame.pack(fill="x", padx=0, pady=0)
            
            tk.Label(header_frame, text=f"📊 JSON Summary - Job {job_id}", 
                     bg="#34495E", fg="#ECF0F1", font=("Segoe UI", 14, "bold")).pack(pady=10)
            tk.Label(header_frame, text=f"📄 {json_file.name}", 
                     bg="#34495E", fg="#95A5A6", font=("Segoe UI", 10)).pack(pady=(0, 10))
            
            # Main content frame
            main_frame = tk.Frame(summary_window, bg="#2C3E50")
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Info labels at top
            info_frame = tk.Frame(main_frame, bg="#34495E")
            info_frame.pack(fill="x", pady=(0, 10))
            
            # Analyze the JSON file
            from collections import defaultdict
            
            try:
                # Get file info
                file_size = json_file.stat().st_size
                modified_time = datetime.fromtimestamp(json_file.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                
                # Load JSON
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Handle different JSON structures
                if isinstance(data, list):
                    listings = data
                elif isinstance(data, dict):
                    if 'data' in data and isinstance(data['data'], list):
                        listings = data['data']
                    elif 'listings' in data and isinstance(data['listings'], list):
                        listings = data['listings']
                    else:
                        listings = [data]
                else:
                    tk.Label(main_frame, text=f"⚠️ Unexpected JSON type: {type(data)}", 
                             bg="#2C3E50", fg="#E74C3C", font=("Segoe UI", 10)).pack(pady=20)
                    return
                
                total_entries = len(listings)
                
                # Display file info
                tk.Label(info_frame, text=f"📊 Size: {file_size:,} bytes  |  🕐 Modified: {modified_time}  |  📋 Entries: {total_entries}", 
                         bg="#34495E", fg="#ECF0F1", font=("Segoe UI", 9)).pack(pady=10)
                
                if total_entries == 0:
                    tk.Label(main_frame, text="⚠️ No entries found in JSON file", 
                             bg="#2C3E50", fg="#E74C3C", font=("Segoe UI", 10)).pack(pady=20)
                    return
                
                # Analyze fields - collect ALL unique values for each field
                field_stats = defaultdict(lambda: {
                    'count': 0,
                    'non_empty': 0,
                    'all_values': []  # Store ALL values found
                })
                
                for entry in listings:
                    if not isinstance(entry, dict):
                        continue
                    
                    for field_name, field_value in entry.items():
                        stats = field_stats[field_name]
                        stats['count'] += 1
                        
                        # Check if non-empty
                        if field_value is not None and field_value != "" and field_value != []:
                            stats['non_empty'] += 1
                            # Store the actual value (convert to string for display)
                            if isinstance(field_value, (list, dict)):
                                value_str = json.dumps(field_value, ensure_ascii=False)
                            else:
                                value_str = str(field_value)
                            stats['all_values'].append(value_str)
                
                # Create tally table with Treeview
                table_frame = tk.Frame(main_frame, bg="#2C3E50")
                table_frame.pack(fill="both", expand=True)
                
                # Create Treeview
                columns = ("Field", "Total", "Non-Empty", "Unique", "Tally")
                tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=20)
                
                # Configure columns
                tree.heading("Field", text="📌 Field Name")
                tree.heading("Total", text="📊 Total")
                tree.heading("Non-Empty", text="✓ Non-Empty")
                tree.heading("Unique", text="🔢 Unique")
                tree.heading("Tally", text="📈 Tally (hover for values)")
                
                tree.column("Field", width=200, anchor="w")
                tree.column("Total", width=80, anchor="center")
                tree.column("Non-Empty", width=100, anchor="center")
                tree.column("Unique", width=80, anchor="center")
                tree.column("Tally", width=400, anchor="w")
                
                # Scrollbar
                scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
                tree.configure(yscrollcommand=scrollbar.set)
                tree.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
                
                # Store tooltips for each row
                field_tooltips = {}
                
                # Populate table
                for field_name in sorted(field_stats.keys()):
                    stats = field_stats[field_name]
                    
                    # Count unique values
                    unique_values = list(set(stats['all_values']))
                    unique_count = len(unique_values)
                    
                    # Create tally string (show count of each unique value)
                    value_counts = defaultdict(int)
                    for val in stats['all_values']:
                        value_counts[val] += 1
                    
                    # Sort by count (most common first)
                    sorted_counts = sorted(value_counts.items(), key=lambda x: x[1], reverse=True)
                    
                    # Create tally display - show summary with click prompt
                    if unique_count <= 3:
                        # If only a few values, show them all inline
                        tally_parts = []
                        for val, count in sorted_counts:
                            display_val = val[:30] + "..." if len(val) > 30 else val
                            tally_parts.append(f"{display_val} ({count}×)")
                        tally_display = " | ".join(tally_parts)
                    else:
                        # Show top 3 and a "Click to view all" prompt
                        tally_parts = []
                        for val, count in sorted_counts[:3]:
                            display_val = val[:30] + "..." if len(val) > 30 else val
                            tally_parts.append(f"{display_val} ({count}×)")
                        tally_display = " | ".join(tally_parts) + f" ... 🔍 Click to view all {unique_count}"
                    
                    # Insert row
                    item_id = tree.insert("", "end", values=(
                        field_name,
                        stats['count'],
                        f"{stats['non_empty']} ({stats['non_empty']*100//stats['count'] if stats['count'] > 0 else 0}%)",
                        unique_count,
                        tally_display
                    ))
                    
                    # (Removed old tooltip code - now using click popup)
                    # Dead code removed - tooltip system replaced with click popup
                    tooltip_lines = []  # Initialize to prevent errors (not used anymore)
                    tooltip_lines.append(f"✓ Non-empty: {stats['non_empty']}")
                    tooltip_lines.append(f"� Unique values: {unique_count}")
                    tooltip_lines.append("")
                    tooltip_lines.append("📈 COMPLETE TALLY:")
                    tooltip_lines.append("─" * 60)
                    
                    # Show ALL values with their counts
                    # (Removed - now using click popup instead)
                    
                    # Store data for click popup instead of tooltip
                    field_tooltips[item_id] = {
                        'field_name': field_name,
                        'stats': stats,
                        'sorted_counts': sorted_counts,
                        'unique_count': unique_count
                    }
                
                # Click handler to show full tally in popup
                def show_tally_popup(event):
                    # Get item and column under cursor
                    item = tree.identify_row(event.y)
                    column = tree.identify_column(event.x)
                    
                    # Only respond to clicks on Tally column (#5)
                    if item and column == "#5" and item in field_tooltips:
                        data = field_tooltips[item]
                        field_name = data['field_name']
                        stats = data['stats']
                        sorted_counts = data['sorted_counts']
                        unique_count = data['unique_count']
                        
                        # Create popup window
                        popup = tk.Toplevel(summary_window)
                        popup.title(f"Complete Tally - {field_name}")
                        popup.geometry("700x600")
                        popup.configure(bg="#2C3E50")
                        
                        # Header
                        header = tk.Frame(popup, bg="#34495E", height=60)
                        header.pack(fill="x", pady=(0, 10))
                        header.pack_propagate(False)
                        
                        tk.Label(
                            header,
                            text=f"{field_name}",
                            bg="#34495E",
                            fg="#ECF0F1",
                            font=("Segoe UI", 14, "bold")
                        ).pack(side="left", padx=20, pady=15)
                        
                        tk.Label(
                            header,
                            text=f"{unique_count} unique values",
                            bg="#34495E",
                            fg="#95A5A6",
                            font=("Segoe UI", 10)
                        ).pack(side="left", padx=10, pady=15)
                        
                        # Create treeview for tally
                        tally_frame = tk.Frame(popup, bg="#2C3E50")
                        tally_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
                        
                        # Scrollbar
                        scrollbar = ttk.Scrollbar(tally_frame)
                        scrollbar.pack(side="right", fill="y")
                        
                        # Treeview
                        tally_tree = ttk.Treeview(
                            tally_frame,
                            columns=("value", "count", "percentage"),
                            show="headings",
                            yscrollcommand=scrollbar.set,
                            height=20
                        )
                        tally_tree.pack(side="left", fill="both", expand=True)
                        scrollbar.config(command=tally_tree.yview)
                        
                        # Configure columns
                        tally_tree.heading("value", text="Value")
                        tally_tree.heading("count", text="Count")
                        tally_tree.heading("percentage", text="Percentage")
                        
                        tally_tree.column("value", width=450, anchor="w")
                        tally_tree.column("count", width=100, anchor="center")
                        tally_tree.column("percentage", width=100, anchor="center")
                        
                        # Store raw data for sorting
                        tally_data = []
                        
                        # Populate with all values
                        total_entries = stats['count']  # Use 'count' instead of 'total'
                        for val, count in sorted_counts:
                            # Show full value (truncate only if extremely long)
                            display_val = val if len(val) <= 200 else val[:200] + "..."
                            percentage = (count / total_entries * 100) if total_entries > 0 else 0
                            
                            # Store raw data for sorting
                            tally_data.append({
                                'value': display_val,
                                'count': count,
                                'percentage': percentage
                            })
                            
                            tally_tree.insert("", "end", values=(
                                display_val,
                                f"{count}×",
                                f"{percentage:.1f}%"
                            ))
                        
                        # Sorting state
                        sort_state = {'column': 'count', 'reverse': True}  # Default: sort by count descending
                        
                        def sort_column(col):
                            """Sort treeview by column"""
                            # Toggle sort direction if clicking same column
                            if sort_state['column'] == col:
                                sort_state['reverse'] = not sort_state['reverse']
                            else:
                                sort_state['column'] = col
                                sort_state['reverse'] = (col != 'value')  # Descending for count/percentage, ascending for value
                            
                            # Sort the data
                            sorted_data = sorted(tally_data, key=lambda x: x[col], reverse=sort_state['reverse'])
                            
                            # Clear tree
                            for item in tally_tree.get_children():
                                tally_tree.delete(item)
                            
                            # Repopulate with sorted data
                            for row in sorted_data:
                                tally_tree.insert("", "end", values=(
                                    row['value'],
                                    f"{row['count']}×",
                                    f"{row['percentage']:.1f}%"
                                ))
                            
                            # Update column headers to show sort direction
                            arrow = " ▼" if sort_state['reverse'] else " ▲"
                            tally_tree.heading("value", text=f"Value{arrow if col == 'value' else ''}")
                            tally_tree.heading("count", text=f"Count{arrow if col == 'count' else ''}")
                            tally_tree.heading("percentage", text=f"Percentage{arrow if col == 'percentage' else ''}")
                        
                        # Bind column clicks to sorting
                        tally_tree.heading("value", text="Value", command=lambda: sort_column('value'))
                        tally_tree.heading("count", text="Count ▼", command=lambda: sort_column('count'))  # Default sort indicator
                        tally_tree.heading("percentage", text="Percentage", command=lambda: sort_column('percentage'))
                        
                        # Close button
                        btn_frame = tk.Frame(popup, bg="#2C3E50")
                        btn_frame.pack(fill="x", padx=20, pady=(0, 20))
                        
                        tk.Button(
                            btn_frame,
                            text="Close",
                            command=popup.destroy,
                            bg="#95A5A6",
                            fg="#fff",
                            font=("Segoe UI", 10),
                            relief="flat",
                            padx=20,
                            pady=5
                        ).pack(side="right")
                
                # Bind click event to tally column
                tree.bind("<Button-1>", show_tally_popup)
                
            except json.JSONDecodeError as je:
                tk.Label(main_frame, text=f"❌ JSON Parse Error: {je}", 
                         bg="#2C3E50", fg="#E74C3C", font=("Segoe UI", 10)).pack(pady=20)
            except Exception as e:
                tk.Label(main_frame, text=f"❌ Error analyzing file: {e}", 
                         bg="#2C3E50", fg="#E74C3C", font=("Segoe UI", 10)).pack(pady=20)
                log_exception("JSON analysis error")
            
            # Button frame
            btn_frame = tk.Frame(summary_window, bg="#2C3E50")
            btn_frame.pack(fill="x", padx=10, pady=10)
            
            tk.Button(btn_frame, text="✖ Close", command=summary_window.destroy,
                     bg="#E74C3C", fg="#fff", font=("Segoe UI", 10, "bold"), padx=20, pady=8).pack(side="left", padx=5)
            
        except Exception as e:
            log_to_file(f"[Queue] Error showing JSON summary for job: {e}")
            log_exception("JSON summary for job error")
            if hasattr(self, '_queue_status_label'):
                self._queue_status_label.config(text=f"✗ Summary failed: {str(e)[:40]}")
    
    def _show_edit_dialog(self, job_id, table):
        """Show edit dialog for a job"""
        log_to_file(f"[Queue] _show_edit_dialog called: job_id={job_id}, table={table}")
        try:
            # Fetch job data from database
            job = {}
            is_new_entry = job_id is None
            is_websites_table = str(table).lower() in ('listing_websites', 'websites')
            
            log_to_file(f"[Queue] is_new_entry={is_new_entry}, is_websites={is_websites_table}")
            
            if not is_new_entry:
                log_to_file(f"[Queue] Opening edit dialog for job {job_id} in table {table}")
                
                # Fetch from appropriate database table
                try:
                    import mysql.connector
                    conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                    cursor = conn.cursor(dictionary=True)
                    
                    if is_websites_table:
                        # Fetch from google_places
                        cursor.execute("SELECT id, Website, Name, availability_website FROM google_places WHERE id = %s", (job_id,))
                    else:
                        # Fetch from queue_websites
                        cursor.execute("SELECT * FROM queue_websites WHERE id = %s", (job_id,))
                    
                    job = cursor.fetchone()
                    cursor.close()
                    conn.close()
                    
                    if not job:
                        log_to_file(f"[Queue] ERROR: Job {job_id} not found in database")
                        self._queue_status_label.config(text=f"Job {job_id} not found")
                        return
                    log_to_file(f"[Queue] ✓ Found job in database")
                    log_to_file(f"[Queue] Job data fields: {list(job.keys())}")
                except Exception as db_err:
                    log_to_file(f"[Queue] Database error: {db_err}")
                    self._queue_status_label.config(text=f"Database error: {db_err}")
                    return
                
                # Log all field values being loaded
                log_to_file(f"[Queue] Job data being loaded:")
                for key, value in job.items():
                    log_to_file(f"[Queue]   {key}: {str(value)[:100]}")
            else:
                log_to_file(f"[Queue] Creating new entry for table {table}")
            
            # Create edit dialog - positioned same as Activity Window
            dialog = tk.Toplevel(self._root)
            
            # Format title with tab context
            tab_display = "Extractor→Websites" if is_websites_table else "Extractor→Networks"
            dialog.title(f"{'Create Entry' if is_new_entry else f'Edit Job {job_id}'} - {tab_display}")
            
            # Get screen dimensions - match Activity Window sizing
            screen_width = self._root.winfo_screenwidth()
            screen_height = self._root.winfo_screenheight()
            window_width = int(screen_width * 0.20)  # 20% of screen width (same as Activity Window)
            window_height = int(screen_height * 0.96)  # 96% height
            
            dialog.geometry(f"{window_width}x{window_height}")
            dialog.configure(bg="#2C3E50")
            dialog.transient(self._root)
            dialog.grab_set()
            
            # Position at top-left (same as Activity Window)
            dialog.geometry(f"+0+0")
            
            # Header - compact
            header = tk.Frame(dialog, bg="#34495E", pady=10)
            header.pack(fill="x")
            title_text = "Create New Entry" if is_new_entry else f"Edit Job {job_id}"
            tk.Label(header, text=title_text, bg="#34495E", fg="#ECF0F1", 
                    font=("Segoe UI", 13, "bold")).pack()
            
            # Create scrollable canvas for the form
            canvas = tk.Canvas(dialog, bg="#2C3E50", highlightthickness=0)
            scrollbar = tk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="#2C3E50")
            
            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )
            
            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)
            
            # Create form fields - ALL database fields
            fields = {}
            
            # Define editable fields based on table type
            if is_websites_table:
                # For google_places table (websites tab)
                editable_fields = [
                    ("Website", "text"),
                    ("Name", "text"),
                    ("availability_website", "text")
                ]
            else:
                # For queue_websites table (networks tab)
                editable_fields = [
                    ("link", "text"),
                    ("the_css", "text"),
                    ("capture_mode", "combo"),
                    ("status", "combo"),
                    ("priority", "number"),
                    ("attempts", "number"),
                    ("last_error", "multiline"),
                    ("source_table", "text"),
                    ("source_id", "number"),
                    ("output_json_path", "text"),
                    ("processed_at", "text"),
                    ("hash_key", "text"),
                    ("run_interval_minutes", "number"),
                    ("steps", "multiline"),
                    ("listing_id", "number")
                ]
            
            row = 0
            for field_name, field_type in editable_fields:
                # Field frame - compact styling
                field_frame = tk.Frame(scrollable_frame, bg="#34495E", pady=4, padx=10)
                field_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=2)
                field_frame.grid_columnconfigure(1, weight=1)
                
                # Label - compact
                label_text = field_name.replace("_", " ").title()
                tk.Label(field_frame, text=f"{label_text}:", anchor="w", fg="#ECF0F1", bg="#34495E", 
                        font=("Segoe UI", 9), width=18).grid(row=0, column=0, sticky="w", padx=(0, 8))
                
                # Get the value from job
                field_value = job.get(field_name, "")
                if field_value is None:
                    field_value = ""
                field_value_str = str(field_value)
                
                log_to_file(f"[Queue] Creating field '{field_name}' (type={field_type}), value='{field_value_str[:50]}'")
                print(f"[EDIT] Field '{field_name}': '{field_value_str[:50]}'")
                
                if field_type == "combo":
                    # Dropdown - different values based on field
                    var = tk.StringVar(master=dialog, value=field_value_str)
                    if field_name == "status":
                        combo_values = ["queued", "running", "done", "error"]
                    elif field_name == "capture_mode":
                        combo_values = ["headless", "browser"]
                    else:
                        combo_values = []
                    combo = ttk.Combobox(field_frame, textvariable=var, values=combo_values, 
                                        font=("Segoe UI", 9), state="readonly", height=5)
                    combo.grid(row=0, column=1, sticky="ew", padx=3)
                    fields[field_name] = var
                    log_to_file(f"[Queue] ✓ Created combo for '{field_name}', current value: '{var.get()}'")
                elif field_type == "number":
                    # Number field - compact
                    var = tk.StringVar(master=dialog, value=field_value_str)
                    entry = tk.Entry(field_frame, textvariable=var, bg="#ECF0F1", fg="#2C3E50", 
                                   insertbackground="#2C3E50", font=("Segoe UI", 9), relief="flat", 
                                   borderwidth=1, highlightthickness=1, highlightbackground="#95A5A6")
                    entry.grid(row=0, column=1, sticky="ew", padx=3, ipady=3)
                    fields[field_name] = var
                    log_to_file(f"[Queue] ✓ Created number entry for '{field_name}', current value: '{var.get()}'")
                elif field_type == "multiline":
                    # Multi-line text field - compact
                    text_widget = tk.Text(field_frame, height=3, bg="#ECF0F1", fg="#2C3E50", 
                                         insertbackground="#2C3E50", wrap="word", font=("Segoe UI", 8),
                                         relief="flat", borderwidth=1, highlightthickness=1, 
                                         highlightbackground="#95A5A6")
                    text_widget.insert("1.0", field_value_str)
                    text_widget.grid(row=0, column=1, sticky="ew", padx=3, pady=2)
                    fields[field_name] = text_widget
                    actual_content = text_widget.get("1.0", "end-1c")
                    log_to_file(f"[Queue] ✓ Created text widget for '{field_name}', content length: {len(actual_content)}")
                else:
                    # Regular text field - compact
                    var = tk.StringVar(master=dialog, value=field_value_str)
                    entry = tk.Entry(field_frame, textvariable=var, bg="#ECF0F1", fg="#2C3E50", 
                                   insertbackground="#2C3E50", font=("Segoe UI", 9), relief="flat",
                                   borderwidth=1, highlightthickness=1, highlightbackground="#95A5A6")
                    entry.grid(row=0, column=1, sticky="ew", padx=3, ipady=3)
                    fields[field_name] = var
                    log_to_file(f"[Queue] ✓ Created text entry for '{field_name}', current value: '{var.get()}'")
                row += 1
            
            log_to_file(f"[Queue] ========== EDIT DIALOG COMPLETE ==========")
            log_to_file(f"[Queue] Created {len(fields)} editable fields")
            print(f"[EDIT] Dialog created with {len(fields)} fields")
            
            scrollable_frame.grid_columnconfigure(1, weight=1)
            
            # Add button frame inside scrollable_frame
            button_row_frame = tk.Frame(scrollable_frame, bg="#2C3E50", pady=15)
            button_row_frame.grid(row=row, column=0, columnspan=2, pady=20)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")
            
            # Update/Create button
            def save_changes():
                try:
                    # Build update payload
                    updates = {}
                    for field_name, widget in fields.items():
                        # Check if it's a Text widget (multiline) or StringVar
                        if isinstance(widget, tk.Text):
                            value = widget.get("1.0", "end-1c")  # Get text from Text widget
                        else:
                            value = widget.get()  # Get from StringVar
                        
                        # Convert numbers
                        if field_name in ("priority", "run_interval_minutes", "attempts", "source_id", "listing_id"):
                            try:
                                value = int(value) if value and value.strip() else None
                            except:
                                value = None
                        
                        # Convert empty strings to None for fields that should be NULL
                        if field_name in ("steps", "last_error", "processed_at", "listing_id", "output_json_path") and isinstance(value, str) and not value.strip():
                            value = None
                        
                        updates[field_name] = value
                    
                    # Update database
                    log_to_file(f"[Queue] Saving to database: {updates}")
                    
                    import mysql.connector
                    conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                    cursor = conn.cursor()
                    
                    if is_websites_table:
                        # Update google_places table
                        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
                        query = f"UPDATE google_places SET {set_clause} WHERE id = %s"
                        cursor.execute(query, tuple(list(updates.values()) + [job_id]))
                        log_to_file(f"[Queue] ✓ Updated google_places record {job_id}")
                        self._queue_status_label.config(text=f"✓ Updated website {job_id}")
                    elif is_new_entry:
                        # Insert new entry to queue_websites
                        columns = ', '.join(updates.keys())
                        placeholders = ', '.join(['%s'] * len(updates))
                        query = f"INSERT INTO queue_websites ({columns}) VALUES ({placeholders})"
                        cursor.execute(query, tuple(updates.values()))
                        new_id = cursor.lastrowid
                        log_to_file(f"[Queue] ✓ Created new entry with ID {new_id}")
                        self._queue_status_label.config(text=f"✓ Created entry {new_id}")
                    else:
                        # Update existing entry in queue_websites
                        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
                        query = f"UPDATE queue_websites SET {set_clause} WHERE id = %s"
                        cursor.execute(query, tuple(list(updates.values()) + [job_id]))
                        log_to_file(f"[Queue] ✓ Updated job {job_id}")
                        self._queue_status_label.config(text=f"✓ Updated job {job_id}")
                    
                    conn.commit()
                    cursor.close()
                    conn.close()
                    
                    dialog.destroy()
                    self._refresh_queue_table()
                except Exception as save_err:
                    log_to_file(f"[Queue] Failed to save: {save_err}")
                    log_exception("Save error")
                    self._queue_status_label.config(text=f"✗ Save failed: {str(save_err)[:40]}")
            
            # Buttons directly under form
            btn_text = "✓ Update" if not is_new_entry else "✓ Create"
            tk.Button(button_row_frame, text=btn_text, command=save_changes, bg="#27AE60", fg="white", 
                     font=("Segoe UI", 10, "bold"), padx=25, pady=8, relief="flat", 
                     cursor="hand2", activebackground="#229954").pack(side="left", padx=8)
            tk.Button(button_row_frame, text="✕ Cancel", command=dialog.destroy, bg="#E74C3C", fg="white", 
                     font=("Segoe UI", 10, "bold"), padx=25, pady=8, relief="flat", 
                     cursor="hand2", activebackground="#C0392B").pack(side="left", padx=8)
            
            # Add "Open Website" button for Websites tab
            if is_websites_table and not is_new_entry:
                def open_website():
                    website_url = fields.get('Website', None)
                    if website_url:
                        url = website_url.get() if hasattr(website_url, 'get') else str(website_url)
                        if url and url.strip():
                            import webbrowser
                            # Calculate position to the right of edit dialog
                            edit_x = dialog.winfo_x()
                            edit_width = dialog.winfo_width()
                            x_position = edit_x + edit_width + 10  # 10px gap
                            
                            # Open browser window positioned to the right
                            try:
                                webbrowser.open(url)
                                log_to_file(f"[Queue] Opened website: {url}")
                            except Exception as open_err:
                                log_to_file(f"[Queue] Failed to open website: {open_err}")
                
                tk.Button(button_row_frame, text="🌐 Open Website", command=open_website, bg="#3498DB", fg="white", 
                         font=("Segoe UI", 10, "bold"), padx=20, pady=8, relief="flat", 
                         cursor="hand2", activebackground="#2980B9").pack(side="left", padx=8)
            
        except Exception as e:
            log_to_file(f"[Queue] Failed to show edit dialog: {e}")
            log_exception("Edit dialog error")
            self._queue_status_label.config(text=f"✗ Edit failed: {str(e)[:40]}")
    
    def _show_apartment_listings(self, network_id, filter_type):
        """Show apartment listings for a network with optional filter"""
        try:
            import mysql.connector
            
            # Get selected date
            selected_date = self._selected_date.get()
            
            # Create window
            window = tk.Toplevel(self._root)
            window.title(f"Apartment Listings - Network {network_id} - {filter_type.replace('_', ' ').title()}")
            window.geometry("1200x600")
            window.configure(bg="#2C3E50")
            
            # Header
            header = tk.Frame(window, bg="#34495E", pady=10)
            header.pack(fill="x")
            
            title_text = {
                "price_changes": f"💰 Price Changes - Network {network_id}",
                "added": f"➕ New Listings - Network {network_id}",
                "subtracted": f"➖ Inactive Listings - Network {network_id}",
                "all": f"📋 All Listings - Network {network_id}"
            }.get(filter_type, f"Listings - Network {network_id}")
            
            tk.Label(header, text=title_text, bg="#34495E", fg="#ECF0F1", 
                    font=("Segoe UI", 14, "bold")).pack()
            tk.Label(header, text=f"Date: {selected_date}", bg="#34495E", fg="#BDC3C7",
                    font=("Segoe UI", 10)).pack()
            
            # Main frame with scrollbar
            main_frame = tk.Frame(window, bg="#2C3E50")
            main_frame.pack(fill="both", expand=True, padx=10, pady=10)
            
            # Treeview
            tree_frame = tk.Frame(main_frame, bg="#2C3E50")
            tree_frame.pack(fill="both", expand=True)
            
            # Different columns for price changes vs other filters
            if filter_type == "price_changes":
                columns = ("ID", "Address", "Old Price", "New Price", "Change", "Beds", "Baths", "Sqft", "Changed At")
            else:
                columns = ("ID", "Address", "Price", "Beds", "Baths", "Sqft", "Available", "Status", "Updated")
            
            tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=20)
            
            # Configure columns based on filter type
            if filter_type == "price_changes":
                tree.heading("ID", text="ID")
                tree.heading("Address", text="Address")
                tree.heading("Old Price", text="Old Price")
                tree.heading("New Price", text="New Price")
                tree.heading("Change", text="Change")
                tree.heading("Beds", text="Beds")
                tree.heading("Baths", text="Baths")
                tree.heading("Sqft", text="Sqft")
                tree.heading("Changed At", text="Changed At")
                
                tree.column("ID", width=60, anchor="center")
                tree.column("Address", width=250, anchor="w")
                tree.column("Old Price", width=100, anchor="e")
                tree.column("New Price", width=100, anchor="e")
                tree.column("Change", width=100, anchor="e")
                tree.column("Beds", width=50, anchor="center")
                tree.column("Baths", width=50, anchor="center")
                tree.column("Sqft", width=80, anchor="e")
                tree.column("Changed At", width=140, anchor="center")
            else:
                tree.heading("ID", text="ID")
                tree.heading("Address", text="Address")
                tree.heading("Price", text="Price")
                tree.heading("Beds", text="Beds")
                tree.heading("Baths", text="Baths")
                tree.heading("Sqft", text="Sqft")
                tree.heading("Available", text="Available")
                tree.heading("Status", text="Status")
                tree.heading("Updated", text="Updated")
                
                tree.column("ID", width=60, anchor="center")
                tree.column("Address", width=300, anchor="w")
                tree.column("Price", width=100, anchor="e")
                tree.column("Beds", width=60, anchor="center")
                tree.column("Baths", width=60, anchor="center")
                tree.column("Sqft", width=80, anchor="e")
                tree.column("Available", width=100, anchor="center")
                tree.column("Status", width=80, anchor="center")
                tree.column("Updated", width=140, anchor="center")
            
            # Scrollbars
            vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
            hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=tree.xview)
            tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            
            tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            
            tree_frame.grid_rowconfigure(0, weight=1)
            tree_frame.grid_columnconfigure(0, weight=1)
            
            # Status label
            status_label = tk.Label(window, text="Loading...", bg="#2C3E50", fg="#ECF0F1",
                                   font=("Segoe UI", 10))
            status_label.pack(pady=5)
            
            # Load data in background
            def load_data():
                try:
                    conn = mysql.connector.connect(
                        host='localhost',
                        port=3306,
                        user='local_uzr',
                        password='fuck',
                        database='offta',
                        connect_timeout=10
                    )
                    cursor = conn.cursor()
                    
                    if filter_type == "price_changes":
                        # Get listings with price changes on selected date, including price change info
                        query = """
                            SELECT DISTINCT 
                                al.id, al.full_address, al.price, al.bedrooms, al.bathrooms, 
                                al.sqft, al.available_date, al.active, al.time_updated,
                                pc.new_price, pc.time
                            FROM apartment_listings al
                            INNER JOIN apartment_listings_price_changes pc ON al.id = pc.apartment_listings_id
                            WHERE al.network_id = %s 
                            AND DATE(pc.time) = %s
                            ORDER BY pc.time DESC
                        """
                        cursor.execute(query, (network_id, selected_date))
                    elif filter_type == "added":
                        # Get listings added on selected date (created on that date and active)
                        query = """
                            SELECT id, full_address, price, bedrooms, bathrooms, sqft, 
                                   available_date, active, time_updated
                            FROM apartment_listings
                            WHERE network_id = %s 
                            AND DATE(time_created) = %s
                            AND active = 'yes'
                            ORDER BY time_updated DESC
                        """
                        cursor.execute(query, (network_id, selected_date))
                    elif filter_type == "subtracted":
                        # Get listings deactivated on selected date
                        query = """
                            SELECT id, full_address, price, bedrooms, bathrooms, sqft, 
                                   available_date, active, time_updated
                            FROM apartment_listings
                            WHERE network_id = %s 
                            AND active = 'no'
                            AND DATE(time_updated) = %s
                            ORDER BY time_updated DESC
                        """
                        cursor.execute(query, (network_id, selected_date))
                    else:  # all
                        # Get all active listings for network
                        query = """
                            SELECT id, full_address, price, bedrooms, bathrooms, sqft, 
                                   available_date, active, time_updated
                            FROM apartment_listings
                            WHERE network_id = %s
                            AND active = 'yes'
                            ORDER BY time_updated DESC
                        """
                        cursor.execute(query, (network_id,))
                    
                    rows = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    
                    # Update UI
                    def update_ui():
                        # Clear existing items
                        for item in tree.get_children():
                            tree.delete(item)
                        
                        # Insert rows - different handling for price_changes
                        for i, row in enumerate(rows):
                            if filter_type == "price_changes":
                                # Price changes has extra columns: new_price and change_time
                                listing_id, address, current_price, beds, baths, sqft, available, active, updated, new_price, change_time = row
                                
                                # The new_price in price_changes is the price it changed TO
                                # The current_price in apartment_listings is what it was BEFORE the change (potentially)
                                try:
                                    new_price_val = float(new_price) if new_price else 0
                                    current_price_val = float(current_price) if current_price else 0
                                    
                                    # new_price is what it changed TO, current is likely the old value
                                    # But since the listing updates, current might BE the new price now
                                    # Show: what was recorded as the change
                                    new_price_str = f"${new_price_val:,.0f}"
                                    
                                    # Try to infer old price - if new_price != current, current might be old
                                    if abs(new_price_val - current_price_val) > 0.01:
                                        old_price_str = f"${current_price_val:,.0f}"
                                        change_val = new_price_val - current_price_val
                                    else:
                                        # They're the same, can't determine old price
                                        old_price_str = "Unknown"
                                        change_val = 0
                                    if change_val > 0:
                                        change_str = f"+${change_val:,.0f}"
                                    elif change_val < 0:
                                        change_str = f"-${abs(change_val):,.0f}"
                                    else:
                                        change_str = "$0"
                                except (ValueError, TypeError):
                                    old_price_str = str(current_price) if current_price else "N/A"
                                    new_price_str = str(new_price) if new_price else "N/A"
                                    change_str = "N/A"
                                
                                beds_str = str(beds) if beds else "N/A"
                                baths_str = str(baths) if baths else "N/A"
                                
                                try:
                                    sqft_str = f"{float(sqft):,.0f}" if sqft else "N/A"
                                except (ValueError, TypeError):
                                    sqft_str = str(sqft) if sqft else "N/A"
                                
                                change_time_str = str(change_time) if change_time else "N/A"
                                
                                # Apply row tags
                                tag = "even" if i % 2 == 0 else "odd"
                                tree.insert("", "end", values=(
                                    listing_id, address, old_price_str, new_price_str, change_str,
                                    beds_str, baths_str, sqft_str, change_time_str
                                ), tags=(tag,))
                            else:
                                # Standard listing display
                                listing_id, address, price, beds, baths, sqft, available, active, updated = row
                                
                                # Format values - handle strings and numbers safely
                                try:
                                    price_str = f"${float(price):,.0f}" if price else "N/A"
                                except (ValueError, TypeError):
                                    price_str = str(price) if price else "N/A"
                                
                                beds_str = str(beds) if beds else "N/A"
                                baths_str = str(baths) if baths else "N/A"
                                
                                try:
                                    sqft_str = f"{float(sqft):,.0f}" if sqft else "N/A"
                                except (ValueError, TypeError):
                                    sqft_str = str(sqft) if sqft else "N/A"
                                
                                available_str = str(available) if available else "N/A"
                                active_str = "✓" if active == "yes" else "✗"
                                updated_str = str(updated) if updated else "N/A"
                                
                                # Apply row tags for zebra striping
                                tag = "even" if i % 2 == 0 else "odd"
                                tree.insert("", "end", values=(
                                    listing_id, address, price_str, beds_str, baths_str,
                                    sqft_str, available_str, active_str, updated_str
                                ), tags=(tag,))
                        
                        # Configure tags
                        tree.tag_configure("even", background="#FFFFFF")
                        tree.tag_configure("odd", background="#E6F7FF")
                        
                        # Update status
                        count_text = f"Found {len(rows)} listing{'s' if len(rows) != 1 else ''}"
                        status_label.config(text=count_text)
                        
                        log_to_file(f"[Listings] Loaded {len(rows)} listings for network {network_id}, filter: {filter_type}")
                    
                    window.after(0, update_ui)
                    
                except Exception as e:
                    error_msg = f"Error loading listings: {e}"
                    log_to_file(f"[Listings] {error_msg}")
                    log_exception(f"Listings query error for network {network_id}, filter: {filter_type}")
                    window.after(0, lambda msg=error_msg: status_label.config(text=msg, fg="#E74C3C"))
            
            threading.Thread(target=load_data, daemon=True).start()
            
            # Close button
            close_btn = tk.Button(window, text="✖ Close", command=window.destroy,
                                 bg="#E74C3C", fg="#fff", font=("Segoe UI", 10, "bold"),
                                 padx=20, pady=8)
            close_btn.pack(pady=10)
            
        except Exception as e:
            log_to_file(f"[Listings] Failed to show apartment listings: {e}")
            log_exception("Show listings error")
    
    def _toggle_mailer_table(self):
        """Toggle the mailer/newsletter table visibility"""
        try:
            log_to_file("[Mailer] Toggle called")
            
            # Initialize if first time
            if not hasattr(self, '_mailer_visible'):
                self._mailer_visible = False
            
            if not hasattr(self, '_mailer_frame'):
                self._create_mailer_frame()
            
            if self._mailer_visible:
                # Hide
                log_to_file("[Mailer] Hiding mailer table")
                self._mailer_frame.pack_forget()
                self._mailer_visible = False
                self._root.geometry("1050x500")
            else:
                # Show
                log_to_file("[Mailer] Showing mailer table")
                self._mailer_frame.pack(fill="both", expand=True, padx=10, pady=10)
                self._mailer_visible = True
                
                # Position window 20% from the left edge, using 70% of screen width
                screen_width = self._root.winfo_screenwidth()
                screen_height = self._root.winfo_screenheight()
                x_position = int(screen_width * 0.20)
                window_width = int(screen_width * 0.70)  # 70% of screen width
                window_height = min(600, int(screen_height * 0.85))  # Max 600 or 85% of screen height
                
                self._root.geometry(f"{window_width}x{window_height}+{x_position}+0")
                self._refresh_mailer_table()
        
        except Exception as e:
            log_to_file(f"[Mailer] Toggle error: {e}")
            log_exception("Mailer toggle error")
    
    def _create_mailer_frame(self):
        """Create the mailer/newsletter table frame"""
        try:
            self._mailer_frame = tk.Frame(self._root, bg="#2C3E50")
            
            # Header with title and "Send to All" button
            header = tk.Frame(self._mailer_frame, bg="#34495E", pady=10)
            header.pack(fill="x")
            
            tk.Label(header, text="Newsletter Subscribers", bg="#34495E", fg="#ECF0F1",
                    font=("Segoe UI", 14, "bold")).pack(side="left", padx=15)
            
            # Send to All button
            tk.Button(header, text="📧 Send Email to All", command=self._send_email_to_all,
                     bg="#E67E22", fg="white", font=("Segoe UI", 10, "bold"),
                     padx=15, pady=8, relief="flat", cursor="hand2").pack(side="right", padx=5)
            
            tk.Button(header, text="📱 Send SMS to All", command=self._send_sms_to_all,
                     bg="#9B59B6", fg="white", font=("Segoe UI", 10, "bold"),
                     padx=15, pady=8, relief="flat", cursor="hand2").pack(side="right", padx=5)
            
            # Email type checkboxes frame
            checkbox_frame = tk.Frame(self._mailer_frame, bg="#2C3E50", pady=5)
            checkbox_frame.pack(fill="x", padx=15)
            
            tk.Label(checkbox_frame, text="Email Types:", bg="#2C3E50", fg="#ECF0F1",
                    font=("Segoe UI", 10, "bold")).pack(side="left", padx=(0, 10))
            
            # Initialize checkbox variables
            self._send_price_changes = tk.BooleanVar(value=True)
            self._send_new_listings = tk.BooleanVar(value=True)
            
            tk.Checkbutton(checkbox_frame, text="📊 Price Changes (24h)", variable=self._send_price_changes,
                          bg="#2C3E50", fg="#ECF0F1", selectcolor="#34495E",
                          font=("Segoe UI", 9), activebackground="#2C3E50",
                          activeforeground="#ECF0F1").pack(side="left", padx=5)
            
            tk.Checkbutton(checkbox_frame, text="🏠 New Listings (24h)", variable=self._send_new_listings,
                          bg="#2C3E50", fg="#ECF0F1", selectcolor="#34495E",
                          font=("Segoe UI", 9), activebackground="#2C3E50",
                          activeforeground="#ECF0F1").pack(side="left", padx=5)
            
            # Status label
            self._mailer_status_label = tk.Label(self._mailer_frame, text="", bg="#2C3E50",
                                                 fg="#ECF0F1", font=("Segoe UI", 10))
            self._mailer_status_label.pack(pady=5)
            
            # Tree frame
            tree_frame = tk.Frame(self._mailer_frame, bg="#2C3E50")
            tree_frame.pack(fill="both", expand=True, padx=10, pady=5)
            tree_frame.grid_rowconfigure(0, weight=1)
            tree_frame.grid_columnconfigure(0, weight=1)
            
            # Tree columns
            columns = ("ID", "Name", "Method", "Type", "Last Email", "Last SMS", "Actions")
            self._mailer_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)
            
            # Column headings and widths
            self._mailer_tree.heading("ID", text="ID")
            self._mailer_tree.heading("Name", text="Name")
            self._mailer_tree.heading("Method", text="Contact")
            self._mailer_tree.heading("Type", text="Type")
            self._mailer_tree.heading("Last Email", text="Last Email Sent")
            self._mailer_tree.heading("Last SMS", text="Last SMS Sent")
            self._mailer_tree.heading("Actions", text="Actions")
            
            self._mailer_tree.column("ID", width=50, anchor="center")
            self._mailer_tree.column("Name", width=180, anchor="w")
            self._mailer_tree.column("Method", width=200, anchor="w")
            self._mailer_tree.column("Type", width=80, anchor="center")
            self._mailer_tree.column("Last Email", width=140, anchor="center")
            self._mailer_tree.column("Last SMS", width=140, anchor="center")
            self._mailer_tree.column("Actions", width=120, anchor="center")
            
            # Scrollbars
            vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._mailer_tree.yview)
            hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._mailer_tree.xview)
            self._mailer_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
            
            self._mailer_tree.grid(row=0, column=0, sticky="nsew")
            vsb.grid(row=0, column=1, sticky="ns")
            hsb.grid(row=1, column=0, sticky="ew")
            
            # Bind click event for Actions column
            self._mailer_tree.bind("<Button-1>", self._on_mailer_tree_click)
            
            log_to_file("[Mailer] Frame created")
        
        except Exception as e:
            log_to_file(f"[Mailer] Frame creation error: {e}")
            log_exception("Mailer frame creation error")
    
    def _refresh_mailer_table(self):
        """Refresh the mailer/newsletter table data"""
        try:
            log_to_file("[Mailer] Refreshing table")
            self._mailer_status_label.config(text="Loading...")
            
            def load_data():
                try:
                    import mysql.connector
                    conn = mysql.connector.connect(
                        host='localhost',
                        port=3306,
                        user='local_uzr',
                        password='fuck',
                        database='offta',
                        connect_timeout=10
                    )
                    cursor = conn.cursor(dictionary=True)
                    
                    query = """
                        SELECT id, name, user_id, ip, date, method, method_pin, 
                               method_type, contact_type, website_section,
                               last_email_sent, last_sms_sent
                        FROM newsletter
                        ORDER BY date DESC
                    """
                    cursor.execute(query)
                    rows = cursor.fetchall()
                    
                    cursor.close()
                    conn.close()
                    
                    def update_ui():
                        # Clear tree
                        for item in self._mailer_tree.get_children():
                            self._mailer_tree.delete(item)
                        
                        # Insert rows
                        for idx, row in enumerate(rows):
                            # Format dates
                            import datetime
                            
                            last_email = 'Never'
                            if row.get('last_email_sent'):
                                if isinstance(row['last_email_sent'], str):
                                    last_email = row['last_email_sent'][:16]  # Show YYYY-MM-DD HH:MM
                                else:
                                    last_email = row['last_email_sent'].strftime('%Y-%m-%d %H:%M')
                            
                            last_sms = 'Never'
                            if row.get('last_sms_sent'):
                                if isinstance(row['last_sms_sent'], str):
                                    last_sms = row['last_sms_sent'][:16]
                                else:
                                    last_sms = row['last_sms_sent'].strftime('%Y-%m-%d %H:%M')
                            
                            contact_type = row.get('contact_type', 'email')
                            
                            tag = "even" if idx % 2 == 0 else "odd"
                            self._mailer_tree.insert("", "end", iid=f"M{row['id']}", values=(
                                row['id'],
                                row['name'],
                                row.get('method', 'N/A'),
                                contact_type,
                                last_email,
                                last_sms,
                                "▶️ Send"
                            ), tags=(tag,))
                        
                        # Configure tags
                        self._mailer_tree.tag_configure("even", background="#FFFFFF")
                        self._mailer_tree.tag_configure("odd", background="#E8F8F5")
                        
                        # Update status
                        self._mailer_status_label.config(text=f"Loaded {len(rows)} subscribers")
                        log_to_file(f"[Mailer] Loaded {len(rows)} subscribers")
                    
                    self._root.after(0, update_ui)
                
                except Exception as e:
                    error_msg = f"Error loading subscribers: {e}"
                    log_to_file(f"[Mailer] {error_msg}")
                    log_exception("Mailer data load error")
                    self._root.after(0, lambda: self._mailer_status_label.config(text=error_msg, fg="#E74C3C"))
            
            threading.Thread(target=load_data, daemon=True).start()
        
        except Exception as e:
            log_to_file(f"[Mailer] Refresh error: {e}")
            log_exception("Mailer refresh error")
    
    def _on_mailer_tree_click(self, event):
        """Handle clicks on the mailer tree"""
        try:
            region = self._mailer_tree.identify_region(event.x, event.y)
            if region != "cell":
                return
            
            item = self._mailer_tree.identify_row(event.y)
            column = self._mailer_tree.identify_column(event.x)
            
            if not item or not column:
                return
            
            # Check if Actions column clicked (#7)
            if column == "#7":
                subscriber_id = item.replace("M", "")
                log_to_file(f"[Mailer] Send button clicked for subscriber {subscriber_id}")
                self._send_to_subscriber(subscriber_id)
        
        except Exception as e:
            log_to_file(f"[Mailer] Tree click error: {e}")
            log_exception("Mailer tree click error")
    
    def _send_to_subscriber(self, subscriber_id):
        """Send email and SMS to a single subscriber"""
        try:
            log_to_file(f"[Mailer] Sending to subscriber {subscriber_id}")
            
            # Get subscriber details
            import mysql.connector
            conn = mysql.connector.connect(
                host='localhost',
                port=3306,
                user='local_uzr',
                password='fuck',
                database='offta',
                connect_timeout=10
            )
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM newsletter WHERE id = %s", (subscriber_id,))
            subscriber = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not subscriber:
                self._mailer_status_label.config(text=f"Subscriber {subscriber_id} not found", fg="#E74C3C")
                return
            
            # Check which email types are selected
            send_price_changes = self._send_price_changes.get()
            send_new_listings = self._send_new_listings.get()
            
            if not send_price_changes and not send_new_listings:
                self._mailer_status_label.config(text=f"✗ Please select at least one email type", fg="#E74C3C")
                return
            
            # Build confirmation message
            email_types = []
            if send_price_changes:
                email_types.append("Price Changes (24h)")
            if send_new_listings:
                email_types.append("New Listings (24h)")
            
            # Show confirmation dialog
            response = messagebox.askyesno(
                "Send to Subscriber",
                f"Send emails to:\n\n"
                f"Name: {subscriber['name']}\n"
                f"Contact: {subscriber['method']}\n\n"
                f"Email Types:\n" + "\n".join(f"  • {t}" for t in email_types) + "\n\n"
                f"Continue?"
            )
            
            if response:
                # Call PHP API to send emails
                import requests
                
                contact_type = subscriber.get('contact_type', 'email')
                
                if contact_type in ('email', 'both'):
                    emails_sent = []
                    emails_failed = []
                    
                    # Send Price Changes email if checked
                    if send_price_changes:
                        self._mailer_status_label.config(text=f"Sending price changes to {subscriber['name']}...", fg="#F39C12")
                        
                        try:
                            api_response = requests.post(
                                php_url('send_price_changes.php'),
                                json={'subscriber_id': subscriber_id},
                                timeout=30
                            )
                            
                            log_to_file(f"[Mailer] Price changes API response status: {api_response.status_code}")
                            log_to_file(f"[Mailer] Price changes API response text: {api_response.text[:500]}")
                            
                            if not api_response.text.strip():
                                emails_failed.append("Price Changes (empty response)")
                                log_to_file(f"[Mailer] Price changes API returned empty response")
                            else:
                                result = api_response.json()
                                if result.get('success'):
                                    emails_sent.append(f"Price Changes ({result.get('count', 0)} items)")
                                    log_to_file(f"[Mailer] Successfully sent price changes email to subscriber {subscriber_id}")
                                else:
                                    error = result.get('error', 'Unknown error')
                                    emails_failed.append(f"Price Changes ({error})")
                                    log_to_file(f"[Mailer] Failed to send price changes: {error}")
                        
                        except Exception as api_err:
                            emails_failed.append(f"Price Changes ({str(api_err)[:30]})")
                            log_to_file(f"[Mailer] Price changes API error: {api_err}")
                            log_exception("Price changes email API error")
                    
                    # Send New Listings email if checked
                    if send_new_listings:
                        self._mailer_status_label.config(text=f"Sending new listings to {subscriber['name']}...", fg="#F39C12")
                        
                        try:
                            api_response = requests.post(
                                php_url('send_new_listings.php'),
                                json={'subscriber_id': subscriber_id},
                                timeout=30
                            )
                            
                            log_to_file(f"[Mailer] New listings API response status: {api_response.status_code}")
                            log_to_file(f"[Mailer] New listings API response text: {api_response.text[:500]}")
                            
                            if not api_response.text.strip():
                                emails_failed.append("New Listings (empty response)")
                                log_to_file(f"[Mailer] New listings API returned empty response")
                            else:
                                result = api_response.json()
                                if result.get('success'):
                                    emails_sent.append(f"New Listings ({result.get('count', 0)} items)")
                                    log_to_file(f"[Mailer] Successfully sent new listings email to subscriber {subscriber_id}")
                                else:
                                    error = result.get('error', 'Unknown error')
                                    emails_failed.append(f"New Listings ({error})")
                                    log_to_file(f"[Mailer] Failed to send new listings: {error}")
                        
                        except Exception as api_err:
                            emails_failed.append(f"New Listings ({str(api_err)[:30]})")
                            log_to_file(f"[Mailer] New listings API error: {api_err}")
                            log_exception("New listings email API error")
                    
                    # Show final status
                    if emails_sent and not emails_failed:
                        self._mailer_status_label.config(text=f"✓ Sent: {', '.join(emails_sent)}", fg="#27AE60")
                    elif emails_sent and emails_failed:
                        self._mailer_status_label.config(text=f"⚠ Sent: {', '.join(emails_sent)} | Failed: {', '.join(emails_failed)}", fg="#F39C12")
                    else:
                        self._mailer_status_label.config(text=f"✗ All failed: {', '.join(emails_failed)}", fg="#E74C3C")
                    
                    self._refresh_mailer_table()  # Refresh to show updated timestamp
                else:
                    self._mailer_status_label.config(text=f"Subscriber is not email type", fg="#E67E22")
        
        except Exception as e:
            log_to_file(f"[Mailer] Send to subscriber error: {e}")
            log_exception("Send to subscriber error")
            self._mailer_status_label.config(text=f"Error sending to subscriber {subscriber_id}", fg="#E74C3C")
    
    def _send_email_to_all(self):
        """Send email to all subscribers"""
        try:
            log_to_file("[Mailer] Send email to all clicked")
            
            response = messagebox.askyesno(
                "Send Email to All",
                "This will send an email to ALL subscribers.\n\n"
                "Are you sure you want to continue?"
            )
            
            if response:
                # Call PHP API to send bulk emails
                import requests
                
                self._mailer_status_label.config(text="Sending emails to all subscribers...", fg="#F39C12")
                log_to_file("[Mailer] Bulk email send initiated")
                
                def send_bulk():
                    try:
                        api_response = requests.post(
                            php_url('send_email_api.php'),
                            json={
                                'action': 'send_to_all',
                                'subject': 'Update from SeattleListed',
                                'message': '<h2>Newsletter Update</h2><p>This is a bulk email from the mailer system.</p>'
                            },
                            timeout=300  # 5 minutes timeout for bulk send
                        )
                        
                        result = api_response.json()
                        
                        if result.get('success'):
                            sent = result.get('sent_count', 0)
                            failed = result.get('failed_count', 0)
                            msg = f"✓ Sent: {sent}, Failed: {failed}"
                            self._root.after(0, lambda: self._mailer_status_label.config(text=msg, fg="#27AE60"))
                            self._root.after(0, self._refresh_mailer_table)
                            log_to_file(f"[Mailer] Bulk send complete: {msg}")
                        else:
                            error = result.get('error', 'Unknown error')
                            self._root.after(0, lambda: self._mailer_status_label.config(text=f"✗ Failed: {error}", fg="#E74C3C"))
                            log_to_file(f"[Mailer] Bulk send failed: {error}")
                    
                    except Exception as api_err:
                        self._root.after(0, lambda: self._mailer_status_label.config(text=f"✗ API Error: {str(api_err)[:50]}", fg="#E74C3C"))
                        log_to_file(f"[Mailer] Bulk API error: {api_err}")
                        log_exception("Bulk email API error")
                
                # Run in background thread
                threading.Thread(target=send_bulk, daemon=True).start()
        
        except Exception as e:
            log_to_file(f"[Mailer] Send email to all error: {e}")
            log_exception("Send email to all error")
    
    def _send_sms_to_all(self):
        """Send SMS to all subscribers"""
        try:
            log_to_file("[Mailer] Send SMS to all clicked")
            
            response = messagebox.askyesno(
                "Send SMS to All",
                "This will send an SMS to ALL subscribers.\n\n"
                "Are you sure you want to continue?"
            )
            
            if response:
                # TODO: Implement bulk SMS sending logic
                self._mailer_status_label.config(text="Sending SMS to all subscribers...", fg="#F39C12")
                log_to_file("[Mailer] Bulk SMS send initiated")
                # After sending completes:
                # self._mailer_status_label.config(text="SMS sent successfully", fg="#27AE60")
        
        except Exception as e:
            log_to_file(f"[Mailer] Send SMS to all error: {e}")
            log_exception("Send SMS to all error")
    
    def _execute_step(self, job_id, table, step):
        """Execute the actual step logic"""
        from datetime import datetime
        try:
            log_to_file(f"[Queue] ========== EXECUTE STEP START ==========")
            log_to_file(f"[Queue] Executing step '{step}' for job {job_id} in table {table}")
            
            # Get job details from cache
            job_id_str = str(job_id)
            log_to_file(f"[Queue] Looking for job {job_id_str} in cache...")
            log_to_file(f"[Queue] Cache keys: {list(self._job_data_cache.keys())}")
            
            if job_id_str in self._job_data_cache:
                job = self._job_data_cache[job_id_str]
                log_to_file(f"[Queue] ✓ Found job in cache")
            else:
                # Fallback: try to get from API
                log_to_file(f"[Queue] ✗ Job not in cache, fetching from API...")
                api_url = f"https://api.trustyhousing.com/manual_upload/queue_website_api.php?table={table}&status=all&limit=1000"
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                
                if isinstance(data, dict):
                    job_data = data.get('data', [])
                    # Find the specific job by ID
                    job = None
                    for j in job_data:
                        if str(j.get('id')) == job_id_str:
                            job = j
                            break
                    if not job:
                        raise Exception(f"Job {job_id} not found in API response")
                else:
                    raise Exception("Invalid API response")
            
            link = job.get('link', '')
            the_css = job.get('the_css', '')
            
            log_to_file(f"[Queue] Job details:")
            log_to_file(f"[Queue]   - Link: {link}")
            log_to_file(f"[Queue]   - CSS: {the_css}")
            log_to_file(f"[Queue]   - Step: {step}")
            
            # Execute based on step type
            if step == "capture_html":
                # Step 1: Capture HTML
                # Pass table to avoid accessing Tk variables off the main thread
                result = self._step_capture_html(job_id, link, the_css, table)
                # Clear any prior local error override for this step
                try:
                    key_override = (str(job_id), table, 'capture_html')
                    if key_override in self._local_step_overrides:
                        del self._local_step_overrides[key_override]
                except Exception as _clr:
                    log_to_file(f"[Queue] Clear override failed: {_clr}")
                
            elif step == "create_json":
                # Step 2: Create JSON using OpenAI
                result = self._step_create_json(job_id, link)
                
            elif step == "manual_match":
                # Step 3: Manual match (includes image extraction and upload)
                result = self._step_manual_match(job_id, link)
                
            elif step == "process_db":
                # Step 4: Process JSON and insert into DB
                result = self._step_process_db(job_id)
                
            elif step == "insert_db":
                # Step 5: Insert into DB
                result = self._step_insert_db(job_id, table)
                
            elif step == "address_match":
                # Step 6: Address Match - show addresses from JSON
                result = self._step_address_match(job_id)
                
            else:
                raise Exception(f"Unknown step: {step}")
            
            # Mark step as done for synchronous steps only. For UI/long-running windows, leave as running.
            if step in ("insert_db", "address_match"):
                def _refresh_ui_running():
                    self._queue_status_label.config(text=f"↻ {step} running for job {job_id} (window opened)")
                    self._refresh_queue_table()
                self._root.after(100, _refresh_ui_running)
            else:
                self._update_step_status(job_id, table, step, "done", result)
                def _refresh_ui():
                    self._queue_status_label.config(text=f"✓ {step} completed for job {job_id}")
                    self._refresh_queue_table()
                self._root.after(100, _refresh_ui)
            
        except Exception as e:
            log_to_file(f"[Queue] Step {step} failed for job {job_id}: {e}")
            log_exception(f"Execute step {step} error")
            
            # Mark step as error
            self._update_step_status(job_id, table, step, "error", str(e))
            # Record local override so UI can show ✗ with hover text even if API failed
            try:
                key_override = (str(job_id), table, step)
                self._local_step_overrides[key_override] = {
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            except Exception as _ov:
                log_to_file(f"[Queue] Failed to record local override: {_ov}")
            
            # Avoid referencing exception var 'e' inside the later-calling closure
            err_text = f"✗ {step} failed: {str(e)[:40]}"
            def _show_error():
                self._queue_status_label.config(text=err_text)
                self._refresh_queue_table()
            
            self._root.after(0, _show_error)
    
    def _update_step_status(self, job_id, table, step, status, message=""):
        """Update step status via API"""
        try:
                api_url = php_url("queue_step_api.php")
                payload = {
                    'table': table,
                    'id': job_id,
                    'step': step,
                    'status': status,
                    'message': message,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                response = requests.post(api_url, json=payload, timeout=10)
                response.raise_for_status()
                log_to_file(f"[Queue] Step {step} status updated to {status}")
        except Exception as e:
            log_to_file(f"[Queue] Failed to update step status: {e}")
    
    # Individual step implementations
    def _check_internet_connection(self):
        """Check if internet is available"""
        try:
            # Try to connect to a reliable host
            response = requests.get("https://www.google.com", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def _show_error_popup(self, title, message):
        """Show an error popup dialog"""
        try:
            import tkinter.messagebox as messagebox
            messagebox.showerror(title, message)
        except Exception as e:
            log_to_file(f"[Queue] Failed to show error popup: {e}")
    
    def _step_capture_html(self, job_id, link, the_css="", table_name: str | None = None, capture_mode="headless"):
        """Step 1: Capture HTML from the URL"""
        from datetime import datetime
        log_to_file(f"[Queue] Capturing HTML for job {job_id} from {link}")
        log_to_file(f"[Queue] Capture mode: {capture_mode}")
        
        # Keep CSS selector exactly as is - DO NOT MODIFY
        if the_css:
            the_css = the_css.strip()  # Only strip whitespace
        
        log_to_file(f"[Queue] CSS selector: {the_css}")
        
        # REMOVED: Auto-opening Chrome at start of Step 1 - only open on 403 error
        # This prevents duplicate Chrome windows when 403 error occurs
        
        # Check internet connection first
        if not self._check_internet_connection():
            error_msg = "No internet connection available. Please check your network and try again."
            log_to_file(f"[Queue] {error_msg}")
            self._root.after(0, lambda: self._show_error_popup("No Internet Connection", error_msg))
            raise Exception(error_msg)
        
        # Get the full page HTML (if headless mode)
        manual_html_captured = False
        
        # Check capture mode
        if capture_mode == "browser":
            # Force browser automation mode
            log_to_file(f"[Queue] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            log_to_file(f"[Queue] 🌐 BROWSER MODE SELECTED")
            log_to_file(f"[Queue] URL: {link}")
            log_to_file(f"[Queue] Starting browser automation...")
            log_to_file(f"[Queue] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            response = None  # Skip HTTP request
        else:
            response = requests.get(link, timeout=30)
        
        # Check for 403 Forbidden error or browser mode
        if capture_mode == "browser" or (response and response.status_code == 403):
            # Determine the reason for browser automation
            if capture_mode == "browser":
                reason = "BROWSER MODE SELECTED"
                status_code_msg = "N/A (browser mode)"
                activity_msg = "🌐 BROWSER MODE - Starting automated capture"
                activity_color = "#00aaff"
            else:
                reason = "403 FORBIDDEN ERROR DETECTED"
                status_code_msg = str(response.status_code)
                activity_msg = "⚠️ 403 FORBIDDEN - Starting automated capture"
                activity_color = "#ff8800"
            
            log_to_file(f"[Queue] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            log_to_file(f"[Queue] ⚠️  {reason}")
            log_to_file(f"[Queue] URL: {link}")
            log_to_file(f"[Queue] Status Code: {status_code_msg}")
            log_to_file(f"[Queue] Starting automated capture process...")
            log_to_file(f"[Queue] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            
            if not the_css:
                mode_text = "Browser mode" if capture_mode == "browser" else "403 Forbidden"
                error_msg = f"{mode_text} requires a CSS selector. Cannot capture element."
                log_to_file(f"[Queue] {error_msg}")
                try:
                    self._root.after(0, lambda: self._show_error_popup("Missing CSS Selector", error_msg))
                except:
                    pass
                raise Exception(error_msg)
            
            log_to_file(f"[Queue] Step 1/3: Opening Chrome browser (20% from left, 80% width, 25% zoom)")
            log_to_file(f"[Queue] CSS selector to capture: {the_css}")
            if hasattr(self, '_activity_logger'):
                self._activity_logger(activity_msg, activity_color)
                self._activity_logger(f"→ Step 1/3: Opening Chrome (selector: {the_css})", "#aaa")
            
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
            
            # Open in Chrome at right side, 80% width, 40% zoom with DevTools auto-opened
            launch_manual_browser_docked_left(link, left_offset_ratio=0.20, width_ratio=0.80, zoom_percent=40.0, auto_open_devtools=True)
            
            # Wait for Chrome and page to load with countdown
            import time
            log_to_file(f"[Queue] Waiting for Chrome and page to fully load...")
            if hasattr(self, '_activity_logger'):
                self._activity_logger("  • Waiting for page to load...", "#888")
            
            for remaining in range(12, 0, -1):
                log_to_file(f"[Queue] Page loading... {remaining} seconds remaining")
                time.sleep(1)
            
            # Check if click coordinates exist in database
            click_x_db = None
            click_y_db = None
            try:
                import mysql.connector
                conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                cursor = conn.cursor()
                cursor.execute("SELECT click_x, click_y FROM queue_websites WHERE id = %s", (job_id,))
                result = cursor.fetchone()
                if result:
                    click_x_db, click_y_db = result
                cursor.close()
                conn.close()
                
                if click_x_db and click_y_db:
                    log_to_file(f"[Queue] ✓ Using saved coordinates from database: ({click_x_db}, {click_y_db})")
            except Exception as db_err:
                log_to_file(f"[Queue] Warning: Could not check database for coordinates: {db_err}")
            
            # Only ask for coordinates if not in database
            if click_x_db and click_y_db:
                coords_result = {'x': click_x_db, 'y': click_y_db, 'cancelled': False}
            else:
                log_to_file(f"[Queue] Requesting click coordinates from user...")
                coords_result = {'x': None, 'y': None, 'cancelled': False}
            
            def ask_for_coordinates():
                """Show dialog to ask for right-click coordinates"""
                coord_dialog = tk.Toplevel(self._root)
                coord_dialog.title("Click Coordinates Required")
                coord_dialog.geometry("450x250")
                coord_dialog.transient(self._root)
                coord_dialog.grab_set()
                
                # Keep dialog always on top in front of browser
                coord_dialog.attributes('-topmost', True)
                coord_dialog.lift()
                coord_dialog.focus_force()
                
                # Center the dialog
                coord_dialog.update_idletasks()
                x = (coord_dialog.winfo_screenwidth() // 2) - (450 // 2)
                y = (coord_dialog.winfo_screenheight() // 2) - (250 // 2)
                coord_dialog.geometry(f"+{x}+{y}")
                
                tk.Label(coord_dialog, text="Right-Click Coordinates", font=("Arial", 14, "bold")).pack(pady=10)
                tk.Label(coord_dialog, text="Hover over the listing element in Chrome and note the mouse position.\nExample: If mouse shows (949, 542), enter those values.", 
                        wraplength=400, justify="left").pack(pady=5)
                
                frame = tk.Frame(coord_dialog)
                frame.pack(pady=10)
                
                tk.Label(frame, text="X coordinate:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
                x_entry = tk.Entry(frame, width=10)
                x_entry.grid(row=0, column=1, padx=5, pady=5)
                x_entry.insert(0, "949")  # Default value
                
                tk.Label(frame, text="Y coordinate:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
                y_entry = tk.Entry(frame, width=10)
                y_entry.grid(row=1, column=1, padx=5, pady=5)
                y_entry.insert(0, "542")  # Default value
                
                def on_ok():
                    try:
                        coords_result['x'] = int(x_entry.get())
                        coords_result['y'] = int(y_entry.get())
                        coord_dialog.destroy()
                    except ValueError:
                        tk.messagebox.showerror("Invalid Input", "Please enter valid integer coordinates")
                
                def on_cancel():
                    coords_result['cancelled'] = True
                    coord_dialog.destroy()
                
                btn_frame = tk.Frame(coord_dialog)
                btn_frame.pack(pady=10)
                tk.Button(btn_frame, text="OK", command=on_ok, width=10).pack(side="left", padx=5)
                tk.Button(btn_frame, text="Cancel", command=on_cancel, width=10).pack(side="left", padx=5)
                
                # Focus on X entry
                x_entry.focus_set()
                x_entry.select_range(0, tk.END)
            
            # Only show dialog if we don't have coordinates
            if coords_result['x'] is None:
                self._root.after(0, ask_for_coordinates)
                
                # Wait for user input
                while coords_result['x'] is None and not coords_result['cancelled']:
                    time.sleep(0.1)
                
                if coords_result['cancelled']:
                    raise Exception("User cancelled coordinate input")
                
                # Save coordinates to database after user input
                if coords_result['x'] and coords_result['y']:
                    try:
                        import mysql.connector
                        conn = mysql.connector.connect(host='localhost', port=3306, user='root', password='', database='offta', connect_timeout=10)
                        cursor = conn.cursor()
                        cursor.execute("UPDATE queue_websites SET click_x = %s, click_y = %s WHERE id = %s", 
                                     (coords_result['x'], coords_result['y'], job_id))
                        conn.commit()
                        cursor.close()
                        conn.close()
                        log_to_file(f"[Queue] ✓ Saved coordinates to database for future use")
                    except Exception as save_err:
                        log_to_file(f"[Queue] Warning: Could not save coordinates to database: {save_err}")
            
            # Calculate 2nd click position based on original proportions
            # Original: (949, 542) -> (997, 707)
            # Offset: +48 right, +165 down
            right_click_x = coords_result['x']
            right_click_y = coords_result['y']
            inspect_click_x = right_click_x + 48
            inspect_click_y = right_click_y + 165
            
            log_to_file(f"[Queue] ✓ Using coordinates: Right-click ({right_click_x}, {right_click_y}), Inspect ({inspect_click_x}, {inspect_click_y})")
            
            # Use pyautogui to automate finding and copying the element from DevTools
            try:
                import pyautogui
                import traceback
                log_to_file(f"[Queue] Step 2/3: Automating DevTools to find and copy element")
                log_to_file(f"[Queue] ═══════════════════════════════════════")
                log_to_file(f"[Queue] Starting automation sequence...")
                log_to_file(f"[Queue] ═══════════════════════════════════════")
                if hasattr(self, '_activity_logger'):
                    self._activity_logger("→ Step 2/3: Automating DevTools", "#aaa")
                
                # Helper to check if paused (uses instance variable to avoid GUI threading issues)
                def wait_if_paused():
                    """Check if automation is paused and wait until resumed"""
                    pause_check_count = 0
                    while True:
                        try:
                            # Check the instance pause variable directly (thread-safe)
                            paused = getattr(self, '_is_paused_403', False)
                            if not paused:
                                break
                            if pause_check_count == 0:
                                log_to_file(f"[Queue] Automation paused, waiting for resume...")
                                if hasattr(self, '_activity_logger'):
                                    self._activity_logger("  ⏸ Paused - waiting...", "#ff8800")
                            time.sleep(0.5)
                            pause_check_count += 1
                        except:
                            break  # If can't check pause state, continue
                
                # Right-click on the page
                try:
                    log_to_file(f"[Queue] → Right-clicking at ({right_click_x}, {right_click_y})")
                    if hasattr(self, '_activity_logger'):
                        self._activity_logger("  • Right-clicking on page", "#888")
                    pyautogui.rightClick(right_click_x, right_click_y)
                    log_to_file(f"[Queue] ✓ Right-click completed")
                    time.sleep(0.5)
                except Exception as e:
                    log_to_file(f"[Queue] ❌ Right-click failed: {e}")
                    log_to_file(f"[Queue] Traceback: {traceback.format_exc()}")
                    raise
                
                wait_if_paused()
                
                # Click to open DevTools "Inspect"
                try:
                    log_to_file(f"[Queue] → Clicking 'Inspect' at ({inspect_click_x}, {inspect_click_y})")
                    if hasattr(self, '_activity_logger'):
                        self._activity_logger("  • Opening DevTools (Inspect)", "#888")
                    pyautogui.click(inspect_click_x, inspect_click_y)
                    log_to_file(f"[Queue] ✓ Inspect click completed - waiting for DevTools to load...")
                    time.sleep(3.0)  # Wait for DevTools/Inspector to fully load
                    log_to_file(f"[Queue] ✓ DevTools should be loaded")
                except Exception as e:
                    log_to_file(f"[Queue] ❌ Inspect click failed: {e}")
                    log_to_file(f"[Queue] Traceback: {traceback.format_exc()}")
                    raise
                
                wait_if_paused()
                
                # Press Ctrl+F to open search in DevTools
                try:
                    log_to_file(f"[Queue] → Opening search (Ctrl+F)")
                    if hasattr(self, '_activity_logger'):
                        self._activity_logger("  • Opening search box (Ctrl+F)", "#888")
                    pyautogui.hotkey('ctrl', 'f')
                    log_to_file(f"[Queue] ✓ Ctrl+F pressed")
                    time.sleep(0.5)  # Longer wait for search box to appear
                except Exception as e:
                    log_to_file(f"[Queue] ❌ Ctrl+F failed: {e}")
                    log_to_file(f"[Queue] Traceback: {traceback.format_exc()}")
                    raise
                
                # Type the CSS selector to search for it
                try:
                    log_to_file(f"[Queue] → Searching for: {the_css}")
                    if hasattr(self, '_activity_logger'):
                        self._activity_logger(f"  • Searching for element: {the_css}", "#888")
                    
                    # Clear search box first (Ctrl+A then type)
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.1)
                    
                    pyautogui.write(the_css, interval=0.05)  # Slower typing
                    log_to_file(f"[Queue] ✓ CSS selector typed: '{the_css}'")
                    time.sleep(0.5)  # Wait for search to process
                except Exception as e:
                    log_to_file(f"[Queue] ❌ Writing CSS selector failed: {e}")
                    log_to_file(f"[Queue] Traceback: {traceback.format_exc()}")
                    raise
                
                # Press Enter to find the element
                try:
                    log_to_file(f"[Queue] → Finding element (Enter)")
                    if hasattr(self, '_activity_logger'):
                        self._activity_logger("  • Pressing Enter to search", "#888")
                    pyautogui.press('enter')
                    log_to_file(f"[Queue] ✓ Enter pressed")
                    log_to_file(f"[Queue] → Waiting 4 seconds for highlight to appear...")
                    time.sleep(4)  # Increased wait time for highlight
                    log_to_file(f"[Queue] ✓ Highlight wait completed")
                except Exception as e:
                    log_to_file(f"[Queue] ❌ Press Enter failed: {e}")
                    log_to_file(f"[Queue] Traceback: {traceback.format_exc()}")
                    raise
                
                wait_if_paused()
                
                # Helper function to safely log to activity window
                def safe_activity_log(msg, color="#888"):
                    try:
                        if hasattr(self, '_activity_logger') and self._activity_logger:
                            self._activity_logger(msg, color)
                    except Exception as e:
                        log_to_file(f"[Queue] Warning: Activity logger failed: {e}")
                
                # Find and click on the highlighted line in inspector code using screenshot
                log_to_file(f"[Queue] → Finding highlighted element in inspector")
                safe_activity_log("  • Locating highlighted element", "#888")
                
                try:
                    # Take a screenshot to find the highlighted element
                    from PIL import Image
                    from datetime import datetime
                    from pathlib import Path
                    import pyautogui
                    
                    # Define the search region (DevTools inspector panel on right side)
                    screen_w = user32.GetSystemMetrics(0) if user32 else 1920
                    screen_h = user32.GetSystemMetrics(1) if user32 else 1080
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    log_to_file(f"[Queue] COORDINATE CALCULATION - STEP BY STEP")
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    log_to_file(f"[Queue] 1. Screen dimensions: {screen_w} x {screen_h}")
                    
                    # Search region: rightmost 20% of screen, full height (DevTools inspector panel)
                    region_left = int(screen_w * 0.8)  # Start at 80% from left (rightmost 20%)
                    region_top = 0  # Start at top
                    region_width = int(screen_w * 0.2)  # 20% width
                    region_height = screen_h  # Full height
                    
                    log_to_file(f"[Queue] 2. Screenshot region calculations:")
                    log_to_file(f"[Queue]    - region_left = {screen_w} * 0.8 = {region_left}")
                    log_to_file(f"[Queue]    - region_top = {region_top}")
                    log_to_file(f"[Queue]    - region_width = {screen_w} * 0.2 = {region_width}")
                    log_to_file(f"[Queue]    - region_height = {region_height}")
                    log_to_file(f"[Queue] 3. Screenshot captures: X from {region_left} to {region_left + region_width}")
                    log_to_file(f"[Queue]                        Y from {region_top} to {region_top + region_height}")
                    
                    # Take screenshot of the DevTools area
                    log_to_file(f"[Queue] → Taking screenshot of DevTools area...")
                    screenshot = pyautogui.screenshot(region=(region_left, region_top, region_width, region_height))
                    log_to_file(f"[Queue] ✓ Screenshot captured: {screenshot.width}x{screenshot.height} pixels")
                    
                    # Save screenshot to Captures folder for debugging
                    captures_dir = Path(__file__).parent / "Captures"
                    captures_dir.mkdir(exist_ok=True)
                    screenshot_path = captures_dir / f"devtools_screenshot_{job_id}_{datetime.now().strftime('%H%M%S')}.png"
                    screenshot.save(screenshot_path)
                    log_to_file(f"[Queue] ✓ Screenshot saved to: {screenshot_path}")
                    safe_activity_log("  • Screenshot saved", "#888")
                    
                    # Search for yellow highlight in the screenshot (from the search match)
                    # Yellow has high R and G, low B (like #FFEB3B or similar)
                    log_to_file(f"[Queue] → Scanning screenshot for yellow highlight...")
                    log_to_file(f"[Queue]    Screenshot size: {screenshot.width}x{screenshot.height}")
                    log_to_file(f"[Queue]    Looking for RGB: R:250-255, G:240-248, B:165-175")
                    safe_activity_log("  • Scanning for yellow highlight", "#888")
                    
                    found_x = None
                    found_y = None
                    pixels_scanned = 0
                    sample_colors = []  # Collect sample RGB values for debugging
                    
                    for y in range(0, screenshot.height, 2):  # Scan entire height, step by 2 for speed
                        for x in range(0, screenshot.width, 5):  # Step by 5 for speed
                            pixels_scanned += 1
                            pixel = screenshot.getpixel((x, y))
                            r, g, b = pixel[0], pixel[1], pixel[2]
                            
                            # Collect sample colors for debugging (every 10,000 pixels)
                            if pixels_scanned % 10000 == 0:
                                sample_colors.append(f"({x},{y})=RGB({r},{g},{b})")
                            
                            # Check for yellow highlight - Chrome search uses #fdf3aa / rgba(253, 243, 170)
                            # Allow slight variation: R: 250-255, G: 240-248, B: 165-175
                            if 250 <= r <= 255 and 240 <= g <= 248 and 165 <= b <= 175:
                                found_x = x
                                found_y = y
                                log_to_file(f"[Queue] ✓ Found yellow highlight at offset ({x}, {y}) RGB({r},{g},{b})")
                                safe_activity_log(f"  • Yellow found at ({x},{y})", "#888")
                                break
                        if found_y is not None:
                            break
                    
                    log_to_file(f"[Queue] → Scanned {pixels_scanned} pixels")
                    log_to_file(f"[Queue] → Sample colors from screenshot:")
                    for sample in sample_colors[:10]:  # Log first 10 samples
                        log_to_file(f"[Queue]    {sample}")
                    
                    if found_y is not None and found_x is not None:
                        click_x = region_left + found_x
                        click_y = region_top + found_y
                        log_to_file(f"[Queue] ═══════════════════════════════════════")
                        log_to_file(f"[Queue] ✓ YELLOW HIGHLIGHT FOUND!")
                        log_to_file(f"[Queue] ═══════════════════════════════════════")
                        log_to_file(f"[Queue] 4. Position in screenshot: ({found_x}, {found_y})")
                        log_to_file(f"[Queue] 5. Converting to screen coordinates:")
                        log_to_file(f"[Queue]    - click_x = region_left + found_x")
                        log_to_file(f"[Queue]    - click_x = {region_left} + {found_x} = {click_x}")
                        log_to_file(f"[Queue]    - click_y = region_top + found_y")
                        log_to_file(f"[Queue]    - click_y = {region_top} + {found_y} = {click_y}")
                        log_to_file(f"[Queue] 6. FINAL CLICK POSITION: ({click_x}, {click_y})")
                        log_to_file(f"[Queue]    - Is this within screen bounds? X: {0} <= {click_x} <= {screen_w}? {0 <= click_x <= screen_w}")
                        log_to_file(f"[Queue]    - Is this within screen bounds? Y: {0} <= {click_y} <= {screen_h}? {0 <= click_y <= screen_h}")
                        log_to_file(f"[Queue] ═══════════════════════════════════════")
                        safe_activity_log(f"  • Found at screen ({click_x}, {click_y})", "#888")
                    else:
                        # No fallback - stop the script
                        log_to_file(f"[Queue] ═══════════════════════════════════════")
                        log_to_file(f"[Queue] ❌ YELLOW HIGHLIGHT NOT FOUND - STOPPING")
                        log_to_file(f"[Queue] ═══════════════════════════════════════")
                        log_to_file(f"[Queue] 4. Yellow highlight was not detected in screenshot")
                        log_to_file(f"[Queue]    - Screenshot region: {region_left}, {region_top}, {region_width}x{region_height}")
                        log_to_file(f"[Queue]    - Pixels scanned: {pixels_scanned}")
                        log_to_file(f"[Queue]    - Stopping automation (no fallback)")
                        log_to_file(f"[Queue] ═══════════════════════════════════════")
                        safe_activity_log(f"  ❌ Highlight not found - stopping", "#ff0000")
                        raise Exception("Yellow highlight not found in screenshot. Cannot continue automation.")
                    
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    log_to_file(f"[Queue] MOVING MOUSE TO TARGET")
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    log_to_file(f"[Queue] 7. Moving mouse to: ({click_x}, {click_y})")
                    safe_activity_log(f"  • Moving to ({click_x},{click_y})", "#888")
                    pyautogui.moveTo(click_x, click_y)
                    log_to_file(f"[Queue] ✓ Mouse moved to target position")
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    log_to_file(f"[Queue] 8. Clicking at: ({click_x}, {click_y})")
                    pyautogui.click(click_x, click_y)
                    log_to_file(f"[Queue] ✓ Click completed at ({click_x}, {click_y})")
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    time.sleep(0.3)
                    
                except Exception as e:
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    log_to_file(f"[Queue] ❌ SCREENSHOT DETECTION FAILED")
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    log_to_file(f"[Queue] Error: {e}")
                    log_to_file(f"[Queue] Stopping automation (no fallback)")
                    log_to_file(f"[Queue] ═══════════════════════════════════════")
                    safe_activity_log("  ❌ Detection failed - stopping", "#ff0000")
                    raise  # Re-raise the exception to stop automation
                
                wait_if_paused()
                
                # Copy element using Ctrl+C directly (no menu navigation)
                log_to_file(f"[Queue] → Copying element with Ctrl+C")
                safe_activity_log("  • Copying element (Ctrl+C)", "#888")
                pyautogui.hotkey('ctrl', 'c')
                log_to_file(f"[Queue] ✓ Ctrl+C pressed - waiting for clipboard to populate...")
                time.sleep(2.0)  # Increased wait for clipboard to populate
                
                # Get HTML from clipboard using main thread
                log_to_file(f"[Queue] Step 3/3: Reading HTML from clipboard")
                if hasattr(self, '_activity_logger'):
                    self._activity_logger("→ Step 3/3: Reading clipboard & saving", "#aaa")
                html_content_holder = [None]
                
                def get_clipboard_content():
                    try:
                        html_content_holder[0] = self._root.clipboard_get()
                        log_to_file(f"[Queue] ✓ Captured {len(html_content_holder[0])} characters from clipboard")
                    except Exception as clip_err:
                        log_to_file(f"[Queue] ✗ Failed to read clipboard: {clip_err}")
                        html_content_holder[0] = None
                
                # Retry clipboard read up to 10 times with increasing delays
                max_retries = 10
                for attempt in range(max_retries):
                    self._root.after(0, get_clipboard_content)
                    time.sleep(1.0 + (attempt * 0.5))  # 1.0s, 1.5s, 2.0s, 2.5s, 3.0s, 3.5s, 4.0s, 4.5s, 5.0s, 5.5s
                    html_content = html_content_holder[0]
                    
                    if html_content and len(html_content) > 100:
                        log_to_file(f"[Queue] ✓ Clipboard read successful on attempt {attempt + 1} ({len(html_content)} chars)")
                        break
                    else:
                        if attempt < max_retries - 1:
                            log_to_file(f"[Queue] ⏳ Clipboard empty/short on attempt {attempt + 1} (got {len(html_content) if html_content else 0} chars), retrying...")
                        else:
                            log_to_file(f"[Queue] ✗ Clipboard still empty after {max_retries} attempts")
                
                if html_content and len(html_content) > 100:
                    # HTML is already the copied element from DevTools - no need to parse again
                    log_to_file(f"[Queue] ✓ Element captured successfully from DevTools")
                    log_to_file(f"[Queue] ✓ Element size: {len(html_content)} characters")
                    if hasattr(self, '_activity_logger'):
                        self._activity_logger(f"  ✓ Captured {len(html_content)} characters", "#00ff00")
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
            if capture_mode == "browser":
                error_msg = "Browser mode requires successful manual capture. No HTML was captured."
                log_to_file(f"[Queue] {error_msg}")
                raise Exception(error_msg)
            
            log_to_file(f"[Queue] DEBUG: No manual capture, using automated request")
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
        else:
            log_to_file(f"[Queue] DEBUG: Using manually captured HTML, skipping automated request")
            log_to_file(f"[Queue] DEBUG: HTML content length before save: {len(html_content)}")
        
        # Save HTML to file
        date_str = datetime.now().strftime("%Y-%m-%d")
        base_html_dir = BASE_DIR / date_str
        
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
        
        # Determine subfolder and prefix based on table
        is_websites = str(table_name).lower() in ('listing_websites', 'websites')
        if is_websites:
            subfolder = "Websites"
            prefix = "google_places"
        else:
            subfolder = "Networks"
            prefix = "networks"
        
        # Create subfolder path
        html_dir = base_html_dir / subfolder
        
        log_to_file(f"[Queue] Creating directory: {html_dir}")
        ensure_dir(html_dir)
        log_to_file(f"[Queue] ✓ Directory created/exists")
        log_to_file(f"[Queue] Filename prefix: {prefix} (table: {table_name}, subfolder: {subfolder})")
        
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
        
        # Get the HTML file path - look in appropriate subfolder based on table
        date_str = datetime.now().strftime("%Y-%m-%d")
        base_html_dir = BASE_DIR / date_str
        
        # Determine which subfolder and prefix to use
        is_websites = str(table_name).lower() in ('listing_websites', 'websites') if table_name else False
        if is_websites:
            html_dir = base_html_dir / "Websites"
            pattern = f"google_places_{job_id}.html"
        else:
            html_dir = base_html_dir / "Networks"
            pattern = f"networks_{job_id}.html"
        
        log_to_file(f"[Queue] Looking for HTML file in: {html_dir}")
        log_to_file(f"[Queue] Pattern: {pattern}")
        
        # Look for HTML file in appropriate subfolder
        html_file = None
        if html_dir.exists():
            for f in html_dir.glob(pattern):
                html_file = f
                log_to_file(f"[Queue] Found matching file: {f}")
                break
        
        if not html_file or not html_file.exists():
            error_msg = f"HTML file not found in {html_dir}/{pattern} - run Step 1 first"
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
        # Import SFTP credentials here to avoid circular import
        from config_helpers import SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS, _sftp_connect, _sftp_ensure_dir
        
        log_to_file(f"[Queue] ========== UPLOAD IMAGES TO SERVER START (WITH CALLBACK) ==========")
        log_to_file(f"[Queue] Uploading images for job {job_id}")
        print(f"[4.DB] Starting image upload for job {job_id}")
        
        # Use thumbnails folder instead of date-based folder
        thumbnails_dir = BASE_DIR / "thumbnails"
        
        if not thumbnails_dir.exists():
            raise Exception("Thumbnails folder not found - run Step 3 first")
        
        # Get list of image files
        image_files = []
        for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
            image_files.extend(list(thumbnails_dir.glob(ext)))
        
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
        
        # Show address match window (auto-opened, not manual)
        show_address_match_window(job_id, self._root, manual_open=False)
        
        return "Address match window opened"

    def _apply_counts(self):
        # Stats chips removed - no longer updating counts
        pass

    def _set_last_line(self, text: str, level: str):
        colors = {
            "muted": "#A0A6AD",
            "ok": "#2ECC71",
            "warn": "#F4D03F",
            "err": "#E74C3C"
        }
        col = colors.get(level, "#A0A6AD")
        
        # Shift existing logs up
        if hasattr(self, '_last_logs') and len(self._last_logs) == 3:
            # Move second log to first position
            self._last_logs[0].config(text=self._last_logs[1].cget("text"), 
                                     fg=self._last_logs[1].cget("fg"))
            # Move third log to second position
            self._last_logs[1].config(text=self._last_logs[2].cget("text"), 
                                     fg=self._last_logs[2].cget("fg"))
            # Add new log to third position
            self._last_logs[2].config(text=text, fg=col)
        else:
            # Fallback for backward compatibility
            self._last.config(text=text, fg=col)
        
        try:
            fill = col
            self._dot.itemconfig(self._dot_id, fill=fill, outline=fill)
        except Exception:
            pass

    # ---------- loader controls ----------
    def _show_loader(self, msg: str = ""):
        try:
            if self._loader:
                self._loader.pack_forget()  # remove if placed elsewhere
                self._loader.pack(fill="x")
            if self._pb:
                try:
                    self._pb.start(12)
                except Exception:
                    pass
            self._set_loader_msg(msg or "Loading…")
        except Exception:
            pass

    def _set_loader_msg(self, msg: str):
        try:
            if self._loader_label:
                self._loader_label.config(text=msg)
        except Exception:
            pass

    def _hide_loader(self):
        try:
            if self._pb:
                try:
                    self._pb.stop()
                except Exception:
                    pass
            if self._loader:
                self._loader.pack_forget()
        except Exception:
            pass

    def mainloop(self):
        try:
            self._root.mainloop()
        except Exception:
            pass

# Singletons / helpers (moved to top of file to avoid circular import)

