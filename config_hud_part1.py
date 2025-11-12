#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re, time, json, logging, sys, threading, queue
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List
from mimetypes import guess_extension
from urllib.parse import urlparse
import traceback as tb
import time

# Third-party deps
import requests
import paramiko
# Database connection not needed - using API instead

# Load environment variables if available

# OldCompactHUD - Part 1

from config_core import *
from config_splash import SplashScreen

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

        # Ensure the window is wide enough to fit Accounts, Notifications, Extractor, Logs, Pause, and controls
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
        
        self._selected_metro = tk.StringVar(value="All")
        metro_container = tk.Frame(metro_row, bg=bg)
        metro_container.pack(side="right", padx=(0, 0))
        
        self._metro_lbl = tk.Label(metro_container, text="Metro:", fg=bg, bg="#2ECC71", font=("Segoe UI", 9, "bold"), padx=6, pady=1)
        self._metro_lbl.pack(side="left", padx=(0, 4))
        self._metro_combo = ttk.Combobox(metro_container, textvariable=self._selected_metro, width=18, state="readonly", values=["All"])
        self._metro_combo.pack(side="left", padx=(0, 0))
        self._metro_combo.current(0)  # Set to first item (All)
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
        sh = root.winfo_screenheight()
        root.geometry(f"360x120+20+{max(0, sh - 180)}")

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
        
        # Date label (today) and table tabs FIRST
        today_str = datetime.now().strftime("%Y-%m-%d")
        date_lbl = tk.Label(tab_header, text=f"Today: {today_str}", fg=muted, bg=chip_bg, font=("Segoe UI", 9, "bold"))
        date_lbl.pack(side="left", padx=(4, 12))
        
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
        
        self._current_status = tk.StringVar(value="queued")
        self._current_table = tk.StringVar(value="listing_networks")
        # Independent status per table
        self._tab_status = {
            "listing_networks": "queued",
            "queue_websites": "queued",
            "parcel": "queued",
            "code": "queued",
            "911": "queued",
            "accounts": "queued",
        }
        
        # Store tab button references and counts
        self._tab_buttons = {}
        self._tab_counts = {}
        
        def make_tab_btn(text, table_name):
            btn = tk.Label(tab_btns_frame, text=text, fg=muted, bg=chip_border, font=("Segoe UI", 8, "bold"), padx=6, pady=1, cursor="hand2")
            btn.pack(side="left", padx=1)
            def on_click(_e):
                try:
                    # Show loading indicator for Networks, Parcel, Code, 911 tabs
                    if table_name.lower() in ('listing_networks', 'networks', 'parcel', 'code', '911'):
                        try:
                            if hasattr(self, '_show_loading'):
                                self._show_loading()
                        except Exception as load_err:
                            log_to_file(f"[Queue] Could not show loading: {load_err}")
                    
                    self._current_table.set(table_name)
                    # Restore per-table status selection
                    try:
                        self._current_status.set(self._tab_status.get(table_name, "queued"))
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
                    self._refresh_queue_table()
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
        tab_networks = make_tab_btn("Networks", "listing_networks")
        tab_websites = make_tab_btn("Websites", "queue_websites")
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
        self._status_counts = {"queued": 0, "running": 0, "done": 0, "error": 0}
        
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
        
        cols = ("ID", "Link", "Interval", "Next Run", "Last Run", "1.HTML", "2.JSON", "3.Extract", "4.Upload", "5.Insert DB", "6.Address Match", "Edit")
        self._queue_tree = ttk.Treeview(tree_frame, columns=cols, show="headings", height=8)

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

        DEFAULT_LABELS = ["ID", "Link", "Interval", "Next Run", "Last Run", "1.HTML", "2.JSON", "3.Extract", "4.Upload", "5.Insert DB", "6.Address Match", "Edit"]
        DEFAULT_WIDTHS = [60, 200, 60, 140, 140, 84, 84, 84, 90, 96, 120, 56]
        _apply_columns(DEFAULT_LABELS, DEFAULT_WIDTHS)

        # Helper to dynamically adjust columns per tab
        def _set_queue_columns_for_table(table_name: str, custom_source: str | None = None):
            t = (table_name or "").lower()
            labels = DEFAULT_LABELS[:]
            widths = DEFAULT_WIDTHS[:]
            try:
                if t in ("queue_websites", "listing_websites", "websites") or custom_source == "websites":
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
                elif t in ("listing_networks", "queue_networks", "networks"):
                    labels[1] = "Link"
                    labels[2] = "CSS"
                    # Replace Next Run with a Summary column to show live stats
                    labels[3] = "Summary"
                    labels[4] = "Last Run"
                    widths[1] = 260
                    widths[2] = 160
                    # Make Summary wider to fit compact metrics
                    widths[3] = 420
                    widths[4] = 140
                    # Hide step columns for Networks table (1.HTML .. 6.Address Match)
                    try:
                        for idx in (5, 6, 7, 8, 9, 10):
                            widths[idx] = 0
                            labels[idx] = ""
                    except Exception:
                        pass
                # otherwise default
            except Exception as _maperr:
                log_to_file(f"[Queue] Column mapping error: {_maperr}")
            _apply_columns(labels, widths)
        self._set_queue_columns_for_table = _set_queue_columns_for_table

        # Local overrides and tooltips for per-cell messages (e.g., capture errors)
        self._local_step_overrides = {}
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
                    
                    # Get screen dimensions and calculate 20% width
                    screen_width = self._root.winfo_screenwidth()
                    window_width = int(screen_width * 0.20)  # 20% of screen width
                    window_height = self._root.winfo_screenheight() - 100  # Nearly full height
                    
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
                    # Dynamic window title based on current tab
                    try:
                        tab_map = {
                            'listing_networks': 'Networks',
                            'queue_networks': 'Networks',
                            'networks': 'Networks',
                            'queue_websites': 'Websites',
                            'websites': 'Websites',
                            'parcel': 'Parcel',
                            'code': 'Code',
                            '911': '911',
                            'accounts': 'Accounts'
                        }
                        friendly_tab = tab_map.get(str(current_table).lower(), str(table).title())
                    except Exception:
                        friendly_tab = str(table).title() if table else "Task"
                    status_win.title(f"{friendly_tab} - {job_id} - Activity Monitor")
                    status_win.geometry(f"{window_width}x{window_height}+0+0")  # 20% width at top-left (0,0)
                    status_win.attributes('-topmost', True)
                    
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
                            if tbl_now not in ('listing_networks', 'queue_networks', 'networks'):
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
                    
                    # Main container
                    main_frame = tk.Frame(status_win, bg="#1e1e1e")
                    main_frame.pack(fill="both", expand=True)
                    
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
                    
                    # Activity window content (no tabs, just single view)
                    activity_label = tk.Label(main_frame, text="Activity Window", font=("Arial", 9, "bold"), bg="#1e1e1e", fg="#00ff00")
                    activity_label.pack(pady=(5,5))
                    
                    # Pause/Resume buttons
                    is_paused = [False]  # Use list to allow modification in nested functions
                    
                    button_frame = tk.Frame(main_frame, bg="#1e1e1e")
                    button_frame.pack(pady=(0,5))
                    
                    def toggle_pause():
                        is_paused[0] = not is_paused[0]
                        if is_paused[0]:
                            pause_btn.config(text="▶ Resume", bg="#00aa00")
                            log_activity("\n⏸️ PAUSED - Click Resume to continue", "#ffaa00")
                        else:
                            pause_btn.config(text="⏸ Pause", bg="#2d2d2d")
                            log_activity("▶️ RESUMED\n", "#00ff00")
                    
                    pause_btn = tk.Button(button_frame, text="⏸ Pause", command=toggle_pause, 
                                         bg="#2d2d2d", fg="#fff", font=("Consolas", 8), 
                                         relief="flat", padx=10, pady=4, cursor="hand2")
                    pause_btn.pack(side="left", padx=2)
                    
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
                        activity_text.insert("end", msg + "\n", color)
                        activity_text.see("end")
                        activity_text.update()
                    
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
                        overall_progress_bar['value'] = current_step
                        remaining_steps = 6 - current_step
                        est_time = sum(avg_step_times[i] for i in range(current_step, 6))
                        
                        if est_time < 60:
                            time_str = f"{est_time}s"
                        else:
                            mins = int(est_time // 60)
                            secs = int(est_time % 60)
                            time_str = f"{mins}m {secs}s"
                        
                        overall_progress_label.config(text=f"Step {current_step}/6 - {steps[current_step-1] if current_step > 0 else 'Starting...'}")
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
                            return
                        
                        # Check if previous steps are completed (for auto-continue)
                        if idx > 0 and not step_completed[idx - 1]:
                            log_activity(f"\n❌ Cannot auto-continue to {steps[idx]} - previous step failed!", "#ff0000")
                            return
                        
                        # Update overall progress
                        update_overall_progress(idx)
                        
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
                        """Step 1: Fetch HTML"""
                        try:
                            status_win.after(0, lambda: log_activity("Starting HTML capture...", "#aaa"))
                            import requests
                            import os
                            import time
                            from bs4 import BeautifulSoup
                            # Build the URL for the HTML source (customize as needed)
                            html_url = self._get_html_url(job_id, table) if hasattr(self, '_get_html_url') else None
                            date_str = datetime.now().strftime("%Y-%m-%d")
                            today_captures_dir = os.path.join(os.path.dirname(__file__), "Captures", date_str)
                            if not os.path.exists(today_captures_dir):
                                os.makedirs(today_captures_dir)
                            html_path = os.path.join(today_captures_dir, f"networks_{job_id}.html")
                            headless_success = False
                            if html_url:
                                try:
                                    resp = requests.get(html_url, timeout=15)
                                    if resp.status_code == 200:
                                        html_content = resp.text
                                        # Check for expected CSS/style (customize as needed)
                                        soup = BeautifulSoup(html_content, "html.parser")
                                        if soup.find("style") or "css" in html_content:
                                            with open(html_path, "w", encoding="utf-8") as f:
                                                f.write(html_content)
                                            headless_success = True
                                            status_win.after(0, lambda: log_activity("✅ Headless HTML fetch succeeded!", "#00ff00"))
                                        else:
                                            status_win.after(0, lambda: log_activity("⚠️ Headless fetch missing CSS/style, will use Chrome.", "#ffaa00"))
                                    else:
                                        status_win.after(0, lambda: log_activity(f"❌ Headless fetch failed: {resp.status_code}", "#ff0000"))
                                except Exception as fetch_err:
                                    status_win.after(0, lambda: log_activity(f"❌ Headless fetch error: {fetch_err}", "#ff0000"))
                            if not headless_success:
                                # Fallback: open Chrome to fetch HTML (existing logic)
                                self._start_job_step(job_id, table, "capture_html")
                                time.sleep(2)
                                # Try to find the HTML file in today's folder only
                                html_path = None
                                if os.path.exists(today_captures_dir):
                                    for file in os.listdir(today_captures_dir):
                                        if file.endswith('.html') and str(job_id) in file:
                                            html_path = os.path.join(today_captures_dir, file)
                                            break
                            if html_path and os.path.exists(html_path):
                                status_win.after(0, lambda: set_status_path(idx, html_path, open_path))
                                status_win.after(0, lambda: add_path_link(html_path, "📄 HTML"))
                                status_win.after(0, lambda: log_activity("✅ HTML captured!", "#00ff00"))
                                
                                # Close Chrome after HTML is captured
                                try:
                                    import subprocess
                                    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], 
                                                 capture_output=True, timeout=5)
                                    status_win.after(0, lambda: log_activity("  🔒 Chrome closed", "#aaa"))
                                except Exception as chrome_err:
                                    status_win.after(0, lambda: log_activity(f"  ⚠️ Could not close Chrome: {chrome_err}", "#ffaa00"))
                            else:
                                status_win.after(0, lambda: log_activity("  ℹ️ Saved to Captures", "#aaa"))
                            status_win.after(0, lambda: finish_step(idx, auto_continue))
                        except Exception as e:
                            status_win.after(0, lambda: log_activity(f"❌ Step 1 failed: {e}", "#ff0000"))
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                    
                    def execute_step_2(idx, auto_continue=True):
                        """Step 2: Create JSON"""
                        try:
                            status_win.after(0, lambda: log_activity("Creating JSON...", "#aaa"))
                            # Determine the expected JSON filename based on table
                            date_str = datetime.now().strftime("%Y-%m-%d")
                            today_captures_dir = os.path.join(os.path.dirname(__file__), "Captures", date_str)
                            html_path = None
                            json_path = None
                            json_filename = None
                            # Find the HTML file for this job (use actual filename)
                            if os.path.exists(today_captures_dir):
                                for file in os.listdir(today_captures_dir):
                                    if file.endswith('.html') and str(job_id) in file:
                                        html_path = os.path.join(today_captures_dir, file)
                                        # Use HTML filename to determine expected JSON filename
                                        json_filename = os.path.splitext(file)[0] + ".json"
                                        break
                            if not html_path or not json_filename:
                                status_win.after(0, lambda: log_activity(f"❌ HTML file not found for job {job_id}", "#ff0000"))
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                                status_win.after(0, lambda: finish_step_timer(idx))
                                return
                            candidate_path = os.path.join(today_captures_dir, json_filename)
                            # Run PHP script headlessly via requests
                            try:
                                import requests
                                import urllib.parse
                                php_url = "http://localhost/process_html_with_openai.php"
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
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                                status_win.after(0, lambda: finish_step_timer(idx))
                                # Don't continue to next step
                                return
                            elif listing_count == 0:
                                # JSON exists but no listings
                                error_msg = f"No listings found in JSON"
                                status_win.after(0, lambda em=error_msg: log_activity(f"❌ {em}", "#ff0000"))
                                status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌ (0 listings)", fg="#ff0000"))
                                status_win.after(0, lambda: finish_step_timer(idx))
                                # Don't continue to next step
                                return
                            
                            # Success: JSON found with listings
                            # Capture variables for lambda
                            _json_path = json_path
                            _listing_count = listing_count
                            _json_basename = os.path.basename(json_path)
                            
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Success ✅ ({_listing_count} listings)", fg="#00ff00"))
                            status_win.after(0, lambda: log_activity(f"✅ JSON created! ({_listing_count} listings)", "#00ff00"))
                            status_win.after(0, lambda: log_activity(f"  📄 {_json_basename}", "#aaa"))
                            status_win.after(0, lambda: set_status_path(idx, _json_path, open_path))
                            status_win.after(0, lambda: add_path_link(_json_path, "📄 JSON"))
                            status_win.after(0, lambda: set_status_summary(idx, f"📄 {_json_basename} • {_listing_count} listings", "#2ECC71"))
                            
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
                            
                            # AUTO-OPEN JSON Stats window after Step 2 completes
                            def _auto_open_json_stats():
                                try:
                                    import json as _json
                                    with open(_json_path, 'r', encoding='utf-8') as _f:
                                        _data = _json.load(_f)
                                    
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
                                    
                                    # Create auto-popup stats window
                                    stats_win = tk.Toplevel(status_win)
                                    stats_win.title(f"📊 JSON Stats - Job {job_id} - {_listing_count} Listings")
                                    
                                    # Position to the right of Activity Window (20% from left)
                                    screen_w = status_win.winfo_screenwidth()
                                    win_w = int(screen_w * 0.35)  # 35% width for stats window
                                    win_h = status_win.winfo_screenheight() - 100
                                    x_pos = int(screen_w * 0.20) + 10  # Just right of Activity Window
                                    stats_win.geometry(f"{win_w}x{win_h}+{x_pos}+0")
                                    stats_win.configure(bg="#1e1e1e")
                                    stats_win.attributes('-topmost', True)
                                    
                                    # Header with emoji icon
                                    header = tk.Frame(stats_win, bg="#34495E")
                                    header.pack(fill="x", pady=0)
                                    tk.Label(header, text=f"📊 JSON Field Statistics", 
                                            bg="#34495E", fg="#ECF0F1", 
                                            font=("Segoe UI", 12, "bold")).pack(pady=10)
                                    tk.Label(header, text=f"{_listing_count} listings • {len(present_counts)} unique keys", 
                                            bg="#34495E", fg="#95A5A6", 
                                            font=("Consolas", 9)).pack(pady=(0,10))
                                    
                                    # Main content
                                    main = tk.Frame(stats_win, bg="#1e1e1e")
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
                                    
                                    # Bottom buttons
                                    btn_frame = tk.Frame(stats_win, bg="#1e1e1e")
                                    btn_frame.pack(fill="x", pady=8)
                                    
                                    def export_csv():
                                        try:
                                            import csv
                                            from tkinter import filedialog
                                            filename = filedialog.asksaveasfilename(
                                                parent=stats_win,
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
                                    
                                    tk.Button(btn_frame, text="Close", command=stats_win.destroy,
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
                            status_win.after(0, lambda: log_activity(f"❌ Step 2 failed: {e}", "#ff0000"))
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                    
                    def execute_step_3(idx, auto_continue=True):
                        """Step 3: Extract Data (download images) with progress bar"""
                        try:
                            # Find extraction folder first and show at top
                            extract_dir = os.path.join(os.path.dirname(__file__), "Captures")
                            status_win.after(0, lambda: set_status_path(idx, extract_dir, open_path))
                            
                            status_win.after(0, lambda: log_activity("Downloading images...", "#aaa"))
                            status_win.after(0, lambda: progress_frame.pack(fill="x", padx=10, pady=5))
                            status_win.after(0, lambda: add_path_link(extract_dir, "📁 Folder"))
                            
                            # Get initial image count before starting
                            date_str = datetime.now().strftime("%Y-%m-%d")
                            today_captures_dir = os.path.join(os.path.dirname(__file__), "Captures", date_str)
                            images_dir = os.path.join(today_captures_dir, f"networks_{job_id}")
                            
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
                                
                                # Check if images directory was created and has images
                                if os.path.exists(images_dir):
                                    current_count = len([f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))])
                                    if current_count > 0:
                                        # Wait a bit more to make sure all images are downloaded
                                        time.sleep(3)
                                        image_count = len([f for f in os.listdir(images_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp'))])
                                        break
                            
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
                            status_win.after(0, lambda: log_activity(f"❌ Step 3 failed: {e}", "#ff0000"))
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                            status_win.after(0, lambda: progress_frame.pack_forget())
                    
                    def execute_step_4(idx, auto_continue=True):
                        """Step 4: Upload with integrated progress"""
                        try:
                            status_win.after(0, lambda: log_activity("Connecting to server...", "#aaa"))
                            status_win.after(0, lambda: progress_frame.pack(fill="x", padx=10, pady=5))
                            
                            # Get images to upload
                            date_str = datetime.now().strftime("%Y-%m-%d")
                            today_captures_dir = os.path.join(os.path.dirname(__file__), "Captures", date_str)
                            images_dir = os.path.join(today_captures_dir, f"networks_{job_id}")
                            
                            if not os.path.exists(images_dir):
                                raise Exception("Images folder not found - run Step 3 first")
                            
                            # Get list of image files
                            image_files = []
                            for ext in ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']:
                                import glob
                                image_files.extend(glob.glob(os.path.join(images_dir, ext)))
                            
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
                            
                            import threading
                            threading.Thread(target=run_upload, daemon=True).start()
                        except Exception as e:
                            status_win.after(0, lambda: log_activity(f"❌ Step 4 failed: {e}", "#ff0000"))
                            status_win.after(0, lambda: progress_frame.pack_forget())
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
