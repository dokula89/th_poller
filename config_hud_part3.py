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

# OldCompactHUD - Part 3

from config_core import *

                                                html_exists = True
                                            else:
                                                # Search all date folders in Captures for any matching file from previous dates
                                                import glob
                                                pattern = str(BASE_DIR / "*" / f"{prefix}_{job_id}.html")
                                                matching_files = glob.glob(pattern)
                                                if matching_files:
                                                    # Use the most recent file's date
                                                    latest_file = max(matching_files, key=lambda p: os.path.getmtime(p))
                                                    # Extract date from path (e.g., Captures/2025-10-29/networks_1.html)
                                                    file_date = Path(latest_file).parent.name
                                                    # Show Start button with last date next to it
                                                    step1 = f"▶ Start ({file_date})"
                                                    html_exists = True
                                            
                                            # Check for JSON file (Step 2)
                                            json_path = BASE_DIR / date_str / f"{prefix}_{job_id}.json"
                                            json_exists = False
                                            if json_path.exists():
                                                # Today's JSON file exists - show checkmark with today's date
                                                step2 = f"✓ {date_str}"
                                                json_exists = True
                                            else:
                                                # Search all date folders for any matching JSON file
                                                pattern = str(BASE_DIR / "*" / f"{prefix}_{job_id}.json")
                                                matching_json = glob.glob(pattern)
                                                if matching_json:
                                                    # Use the most recent file's date
                                                    latest_json = max(matching_json, key=lambda p: os.path.getmtime(p))
                                                    file_date = Path(latest_json).parent.name
                                                    # Show Start button with last date
                                                    step2 = f"▶ Start ({file_date})"
                                                    json_exists = True
                                            
                                            # Step 2 needs Step 1
                                            if not html_exists and not json_exists:
                                                step2 = "⊘ Need Step 1"
                                            
                                            # Check for images folder (Step 3 - Extract)
                                            images_folder = BASE_DIR / date_str / f"{prefix}_{job_id}"
                                            images_exist = False
                                            image_count = 0
                                            if images_folder.exists() and images_folder.is_dir():
                                                # Count images in folder
                                                image_extensions = ['*.jpg', '*.jpeg', '*.png', '*.gif', '*.webp']
                                                for ext in image_extensions:
                                                    image_count += len(list(images_folder.glob(ext)))
                                                
                                                if image_count > 0:
                                                    step3 = f"✓ {image_count} imgs"
                                                    images_exist = True
                                                else:
                                                    step3 = "⚠️ Empty"
                                            else:
                                                # Search for folder in other date folders
                                                pattern = str(BASE_DIR / "*" / f"{prefix}_{job_id}")
                                                matching_folders = [p for p in glob.glob(pattern) if Path(p).is_dir()]
                                                if matching_folders:
                                                    latest_folder = Path(max(matching_folders, key=lambda p: os.path.getmtime(p)))
                                                    # Count images
                                                    for ext in image_extensions:
                                                        image_count += len(list(latest_folder.glob(ext)))
                                                    file_date = latest_folder.parent.name
                                                    if image_count > 0:
                                                        step3 = f"▶ {image_count} ({file_date})"
                                                        images_exist = True
                                                    else:
                                                        step3 = f"⚠️ Empty ({file_date})"
                                            
                                            # Step 3 needs Step 2 (JSON)
                                            if not json_exists and not images_exist:
                                                step3 = "⊘ Need Step 2"
                                            
                                            # Step 4 (Upload) - only allow if images folder exists and has images
                                            if images_folder.exists() and images_folder.is_dir():
                                                image_count = 0
                                                for ext in image_extensions:
                                                    image_count += len(list(images_folder.glob(ext)))
                                                
                                                if image_count > 0:
                                                    # Check if already uploaded (from step status)
                                                    if isinstance(step_data, dict) and step_data.get("process_db") == "done":
                                                        step4 = f"✓ Uploaded"
                                                    else:
                                                        step4 = f"▶ Upload {image_count}"
                                                else:
                                                    step4 = "⚠️ No images"
                                            else:
                                                step4 = "⊘ Need Step 3"
                                            
                                            # Step 5 needs JSON to be present (allow if JSON exists)
                                            if not json_exists and step5.startswith("▶"):
                                                step5 = "⊘ Need JSON"
                                        except Exception as _filechk_err:
                                            log_to_file(f"[Queue] File presence check failed: {_filechk_err}")
                                    
                                    # Calculate interval and next run info (repurpose for Networks CSS when applicable)
                                    interval_minutes = r.get("run_interval_minutes") or 0
                                    interval_display = f"{interval_minutes}m" if interval_minutes > 0 else "-"
                                    
                                    # Calculate last run and time ago (merged into one column)
                                    last_run_display = "-"
                                    try:
                                        processed_at = r.get("processed_at")
                                        if processed_at:
                                            from datetime import datetime as _dt, timedelta
                                            if isinstance(processed_at, str):
                                                processed_dt = _dt.strptime(processed_at, "%Y-%m-%d %H:%M:%S")
                                            else:
                                                processed_dt = processed_at
                                            
                                            # Calculate time ago
                                            now = _dt.now()
                                            time_diff = now - processed_dt
                                            total_minutes = int(time_diff.total_seconds() / 60)
                                            
                                            # Format: "5m ago" or "2h ago" or "10-30 14:23" for older
                                            if total_minutes < 60:
                                                last_run_display = f"{total_minutes}m ago"
                                            elif total_minutes < 1440:  # Less than 24 hours
                                                hours_ago = total_minutes // 60
                                                last_run_display = f"{hours_ago}h ago"
                                            else:  # More than 24 hours - show date/time
                                                last_run_display = processed_dt.strftime("%m-%d %H:%M")
                                    except Exception as _time_err:
                                        log_to_file(f"[Queue] Failed to calculate last run: {_time_err}")
                                    
                                    # Calculate next run time
                                    next_run_display = "-"
                                    try:
                                        processed_at = r.get("processed_at")
                                        if processed_at and interval_minutes > 0:
                                            from datetime import datetime as _dt, timedelta
                                            if isinstance(processed_at, str):
                                                processed_dt = _dt.strptime(processed_at, "%Y-%m-%d %H:%M:%S")
                                            else:
                                                processed_dt = processed_at
                                            next_run_dt = processed_dt + timedelta(minutes=interval_minutes)
                                            now = _dt.now()
                                            if next_run_dt > now:
                                                minutes_left = int((next_run_dt - now).total_seconds() / 60)
                                                if minutes_left < 60:
                                                    next_run_display = f"{minutes_left}m"
                                                elif minutes_left < 1440:
                                                    hours_left = minutes_left // 60
                                                    next_run_display = f"{hours_left}h"
                                                else:
                                                    days_left = minutes_left // 1440
                                                    next_run_display = f"{days_left}d"
                                            else:
                                                next_run_display = "Ready"
                                    except Exception as _time_err:
                                        log_to_file(f"[Queue] Failed to calculate next run: {_time_err}")

                                    # Parcel tab: override displays to show total addresses, metro, and empty parcels
                                    if str(current_table).lower() == 'parcel' and isinstance(r, dict):
                                        try:
                                            # Column 2 (Interval) -> Total Addresses
                                            total_addr = r.get('total_addresses', 0)
                                            interval_display = str(int(total_addr)) if total_addr else '0'
                                            
                                            # Column 3 (Next Run) -> Metro Name
                                            metro_nm = r.get('metro_name') or '-'
                                            next_run_display = metro_nm
                                            
                                            # Column 4 (Last Run) -> Empty Parcels count
                                            empty_val = r.get('empty_parcels')
                                            last_run_display = (str(int(empty_val)) if (empty_val not in (None, '')) else '0')
                                        except Exception as _parcel_disp_err:
                                            log_to_file(f"[Parcel] Display override failed: {_parcel_disp_err}")
                                    # Websites tab: override to show Name in Next Run
                                    if custom_source == 'websites' and isinstance(r, dict):
                                        next_run_display = r.get('name') or '-'
                                    # Networks tab: show CSS in the 'Interval' column
                                    if str(current_table).lower() in ("listing_networks", "queue_networks", "networks"):
                                        try:
                                            css_val = r.get('the_css') or r.get('css') or '-'
                                            interval_display = str(css_val)[:60]
                                        except Exception as _css_err:
                                            log_to_file(f"[Networks] Failed to map CSS: {_css_err}")
                                    # Accounts tab: override to show display name and role/seen
                                    if custom_source == 'accounts' and isinstance(r, dict):
                                        next_run_display = r.get('name') or '-'
                                        try:
                                            seen = r.get('last_seen') or r.get('registered')
                                            if isinstance(seen, str):
                                                last_seen_display = seen
                                            elif seen is None:
                                                last_seen_display = '-'
                                            else:
                                                last_seen_display = str(seen)
                                            role = r.get('role') or '-'
                                            last_run_display = f"{role} • {last_seen_display}"
                                        except Exception as _acct_disp_err:
                                            log_to_file(f"[Accounts] Display override failed: {_acct_disp_err}")
                                    
                                    item_id = self._queue_tree.insert("", "end", values=(
                                        f"▶ {job_id}",  # Green play button with ID
                                        link,
                                        interval_display,
                                        next_run_display,
                                        last_run_display,
                                        step1,
                                        step2,
                                        step3,
                                        step4,
                                        step5,
                                        step6,
                                        "✎ Edit"
                                    ))
                                    # Attach tooltip if we have a local error override for capture_html
                                    try:
                                        key_override = (str(job_id), table, 'capture_html')
                                        override = self._local_step_overrides.get(key_override)
                                        if override and override.get('status') == 'error':
                                            # Column #6 now corresponds to 1.HTML
                                            err_msg = str(override.get('message') or 'Capture failed')
                                            self._cell_tooltips[(item_id, '#6')] = err_msg
                                    except Exception as _ovr:
                                        log_to_file(f"[Queue] Failed to attach tooltip: {_ovr}")
                                    count += 1
                                except Exception as row_err:
                                    log_to_file(f"[Queue] Error inserting row: {row_err}")
                                    print(f"[Queue] Error inserting row: {row_err}")
                                    continue
                            
                            # Custom status for Parcel tab: show selected metro and empty KCP count
                            if str(current_table).lower() == 'parcel' and parcel_empty_count is not None:
                                sel = selected_metro if (selected_metro and selected_metro != "All") else "All metros"
                                msg = f"Parcel — {sel}: empty king_county_ids = {int(parcel_empty_count)}"
                                self._queue_status_label.config(text=msg)
                            else:
                                # Generic loaded message without relying on outer-scope vars
                                msg = f"✓ Loaded {count} items"
                                self._queue_status_label.config(text=msg)
                            if not silent:
                                log_to_file(f"[Queue] {msg}")
                                print(f"[Queue] {msg}")
                            
                            # Also refresh status counts after loading table
                            if hasattr(self, '_refresh_status_counts'):
                                try:
                                    self._refresh_status_counts(silent=True)
                                except Exception as count_err:
                                    log_to_file(f"[Queue] Count refresh failed: {count_err}")
                            
                        except Exception as e:
                            err_msg = f"UI update failed: {str(e)[:60]}"
                            self._queue_status_label.config(text=err_msg)
                            log_to_file(f"[Queue] {err_msg}")
                            log_exception("UI update error")
                            print(f"[Queue] {err_msg}")
                    
                    if hasattr(self, '_root'):
                        self._root.after(0, _update_ui)
            
            try:
                if not silent:
                    log_to_file("[Queue] Starting background thread")
                threading.Thread(target=_bg_fetch, daemon=True).start()
            except Exception as e:
                log_to_file(f"[Queue] Thread start failed: {e}")
                log_exception("Thread start error")
                print(f"[Queue] Thread start failed: {e}")
                self._queue_status_label.config(text=f"Thread error: {e}")
        
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
                api_table = table
                lock_to_queued_only = False
                if str(current_table).lower() in ("listing_networks", "queue_networks", "networks"):
                    # For Networks tab, show counts from queue_websites and emphasize 'queued' only
                    api_table = "queue_websites"
                    lock_to_queued_only = True
                
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
        
        # Auto-refresh timer - start after 10 seconds to avoid conflicts with initial load
        def _auto_refresh_tick():
            try:
                if self._queue_visible and self._auto_refresh_enabled and not self._refresh_in_progress:
                    # Silent auto refresh (no 'Loading...' or noisy logs)
                    self._refresh_queue_table(silent=True)
                
                # Also refresh counts every cycle (whether table is visible or not)
                if self._auto_refresh_enabled and not self._counts_refresh_in_progress:
                    self._refresh_status_counts(silent=True)
            except Exception as e:
                log_to_file(f"[Queue] Auto-refresh error: {e}")
            finally:
                root.after(5000, _auto_refresh_tick)  # Schedule next check
        
        root.after(10000, _auto_refresh_tick)  # First check after 10 seconds
        
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
                            api_url = f"http://localhost/step5/get_accounts.php"
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
                sh = root.winfo_screenheight()
                new_h = 500
                new_w = 900
                x_pos = 20
                y_pos = max(0, sh - (new_h + 60))
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
                        sh = root.winfo_screenheight()
                        new_h = 500
                        new_w = 1050  # Adjusted width for 11 columns (merged Last Run + Time Ago)
                        x_pos = 20
                        y_pos = max(0, sh - (new_h + 60))
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
                        sh = root.winfo_screenheight()
                        new_h = 120
                        new_w = 360
                        x_pos = 20
                        y_pos = max(0, sh - 180)
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
        
        # Bind Mailer button - placeholder for future mailer functionality
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
                
                # Show placeholder message
                self._set_last_line("Mailer functionality coming soon...", "info")
                
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
                # Placeholder for future functionality
                from tkinter import messagebox
                messagebox.showinfo("Notifications", 
                                  "Notifications Center\n\nComing soon...",
                                  parent=root)
            except Exception as ex:
                log_to_file(f"[Notifications] Notifications button handler error: {ex}")
                print(f"[Notifications] Notifications button handler error: {ex}")
        notifications_btn.bind("<Button-1>", _on_notifications_btn)
        
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
                    api_url = "http://localhost/queue_step_api.php"
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
        try:
            # Get job data from cache or API
            job_id_str = str(job_id)
            
            log_to_file(f"[Queue] ========== EDIT DIALOG ==========")
            log_to_file(f"[Queue] Opening edit dialog for job {job_id} in table {table}")
            log_to_file(f"[Queue] Checking cache for job {job_id_str}")
            log_to_file(f"[Queue] Cache keys: {list(self._job_data_cache.keys())}")
            
            if job_id_str in self._job_data_cache:
                job = self._job_data_cache[job_id_str]
                log_to_file(f"[Queue] ✓ Found job in cache")
                log_to_file(f"[Queue] Job data fields: {list(job.keys())}")
            else:
                # Fetch from API
                log_to_file(f"[Queue] Job not in cache, fetching from API...")
                api_url = f"https://api.trustyhousing.com/manual_upload/queue_website_api.php?table={table}&status=all&limit=1000"
                response = requests.get(api_url, timeout=10)
                response.raise_for_status()
                data = response.json()
                jobs = data.get('data', [])
                job = next((j for j in jobs if str(j.get('id')) == job_id_str), None)
                if not job:
                    log_to_file(f"[Queue] ERROR: Job {job_id} not found in API response")
                    self._queue_status_label.config(text=f"Job {job_id} not found")
                    return
                log_to_file(f"[Queue] ✓ Found job via API")
                log_to_file(f"[Queue] Job data fields: {list(job.keys())}")
            
            # Log all field values being loaded
            log_to_file(f"[Queue] Job data being loaded:")
            for key, value in job.items():
                log_to_file(f"[Queue]   {key}: {str(value)[:100]}")
            
            # Create edit dialog
            dialog = tk.Toplevel(self._root)
            dialog.title(f"Edit Job {job_id} - {table}")
            dialog.geometry("700x700")
            dialog.transient(self._root)
            dialog.grab_set()
            
            # Create scrollable canvas for the form
            canvas = tk.Canvas(dialog, bg="#2C3E50")
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
            
            # Define all editable fields (exclude id, created_at, updated_at which are auto-managed)
            editable_fields = [
                ("link", "text"),
                ("the_css", "text"),
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
                tk.Label(scrollable_frame, text=f"{field_name}:", anchor="w", fg="#ECF0F1", bg="#2C3E50", font=("Segoe UI", 9)).grid(row=row, column=0, sticky="nw", padx=10, pady=5)
                
                # Get the value from job
                field_value = job.get(field_name, "")
                if field_value is None:
                    field_value = ""
                field_value_str = str(field_value)
                
                log_to_file(f"[Queue] Creating field '{field_name}' (type={field_type}), value='{field_value_str[:50]}'")
                print(f"[EDIT] Field '{field_name}': '{field_value_str[:50]}'")
                
                if field_type == "combo":
                    # Dropdown for status
                    var = tk.StringVar(master=dialog, value=field_value_str)
                    combo = ttk.Combobox(scrollable_frame, textvariable=var, values=["queued", "running", "done", "error"], width=50)
                    combo.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
                    fields[field_name] = var
                    log_to_file(f"[Queue] ✓ Created combo for '{field_name}', current value: '{var.get()}'")
                elif field_type == "number":
                    # Number field
                    var = tk.StringVar(master=dialog, value=field_value_str)
                    entry = tk.Entry(scrollable_frame, textvariable=var, width=53, bg="#34495E", fg="#ECF0F1", insertbackground="#ECF0F1")
                    entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
                    fields[field_name] = var
                    log_to_file(f"[Queue] ✓ Created number entry for '{field_name}', current value: '{var.get()}'")
                elif field_type == "multiline":
                    # Multi-line text field
                    text_widget = tk.Text(scrollable_frame, width=50, height=3, bg="#34495E", fg="#ECF0F1", insertbackground="#ECF0F1", wrap="word")
                    text_widget.insert("1.0", field_value_str)
                    text_widget.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
                    fields[field_name] = text_widget
                    actual_content = text_widget.get("1.0", "end-1c")
                    log_to_file(f"[Queue] ✓ Created text widget for '{field_name}', content length: {len(actual_content)}")
                else:
                    # Regular text field
                    var = tk.StringVar(master=dialog, value=field_value_str)
                    entry = tk.Entry(scrollable_frame, textvariable=var, width=53, bg="#34495E", fg="#ECF0F1", insertbackground="#ECF0F1")
                    entry.grid(row=row, column=1, sticky="ew", padx=10, pady=5)
                    fields[field_name] = var
                    log_to_file(f"[Queue] ✓ Created text entry for '{field_name}', current value: '{var.get()}'")
                row += 1
            
            log_to_file(f"[Queue] ========== EDIT DIALOG COMPLETE ==========")
            log_to_file(f"[Queue] Created {len(fields)} editable fields")
            print(f"[EDIT] Dialog created with {len(fields)} fields")
            
            scrollable_frame.grid_columnconfigure(1, weight=1)
            
            # Pack canvas and scrollbar
            canvas.pack(side="left", fill="both", expand=True, pady=(0, 50))
            scrollbar.pack(side="right", fill="y")
            
            # Button frame at bottom (outside canvas)
            button_frame = tk.Frame(dialog, bg="#2C3E50")
            button_frame.pack(side="bottom", fill="x", padx=10, pady=10)
            
            # Save button
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
                        
                        updates[field_name] = value
                    
                    # Call API to update (you'll need to create an update endpoint)
                    # For now, just update the cache and refresh
                    log_to_file(f"[Queue] Saving updates for job {job_id}: {updates}")
                    
                    # Update cache
                    if job_id_str in self._job_data_cache:
                        self._job_data_cache[job_id_str].update(updates)
                    
                    self._queue_status_label.config(text=f"✓ Saved changes to job {job_id}")
                    dialog.destroy()
                    self._refresh_queue_table()
                except Exception as save_err:
                    log_to_file(f"[Queue] Failed to save: {save_err}")
                    log_exception("Save error")
                    self._queue_status_label.config(text=f"✗ Save failed: {str(save_err)[:40]}")
            
            tk.Button(button_frame, text="💾 Save Changes", command=save_changes, bg="#2ECC71", fg="#fff", font=("Segoe UI", 10, "bold"), padx=20, pady=8).pack(side="left", padx=5)
            tk.Button(button_frame, text="✖ Cancel", command=dialog.destroy, bg="#E74C3C", fg="#fff", font=("Segoe UI", 10, "bold"), padx=20, pady=8).pack(side="left", padx=5)
            
        except Exception as e:
            log_to_file(f"[Queue] Failed to show edit dialog: {e}")
            log_exception("Edit dialog error")
            self._queue_status_label.config(text=f"✗ Edit failed: {str(e)[:40]}")
    
    def _execute_step(self, job_id, table, step):
        """Execute the actual step logic"""
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
                api_url = "http://localhost/queue_step_api.php"
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
    
    def _step_capture_html(self, job_id, link, the_css="", table_name: str | None = None):
        """Step 1: Capture HTML from the URL"""
        log_to_file(f"[Queue] Capturing HTML for job {job_id} from {link}")
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
        php_url = f"http://localhost/process_html_with_openai.php?file={file_path_encoded}&model=gpt-4o-mini&method=local&process=1&headless=1"
        
        log_to_file(f"[Queue] ========== CALLING PHP SCRIPT ==========")
        log_to_file(f"[Queue] URL: {php_url}")
        log_to_file(f"[Queue] Original path: {html_file}")
        log_to_file(f"[Queue] Encoded path: {file_path_encoded}")
        log_to_file(f"[Queue] Starting request (timeout=120s)...")
        
        # Print the URL to console as well for easy copy-paste
        print(f"\n{'='*80}")
        print(f"[2.JSON] Calling PHP Script:")
        print(f"URL: {php_url}")
        print(f"{'='*80}\n")
        
        # Update UI to show we're calling PHP
        def _update_status_calling():
            self._queue_status_label.config(text=f"📞 Calling OpenAI PHP script for job {job_id}...")
        self._root.after(0, _update_status_calling)
        
        try:
            response = requests.get(php_url, timeout=120)  # 2 minute timeout for AI processing
            log_to_file(f"[Queue] ✓ Response received!")
            log_to_file(f"[Queue] Status code: {response.status_code}")
            log_to_file(f"[Queue] Content-Type: {response.headers.get('Content-Type', 'N/A')}")
            log_to_file(f"[Queue] Response length: {len(response.text)} chars")
