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

# OldCompactHUD - Part 2

from config_core import *

                    
                    def execute_step_5(idx, auto_continue=True):
                        """Step 5: Insert DB (embedded details tab)"""
                        try:
                            status_win.after(0, lambda: log_activity("Inserting to DB...", "#aaa"))
                            # Load JSON listings
                            from datetime import datetime as _dt
                            date_str = _dt.now().strftime("%Y-%m-%d")
                            json_path = BASE_DIR / date_str / f"networks_{job_id}.json"
                            if not json_path.exists():
                                pattern = str(BASE_DIR / "*" / f"networks_{job_id}.json")
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
                                                host=CFG["MYSQL_HOST"], user=CFG["MYSQL_USER"], password=CFG["MYSQL_PASSWORD"],
                                                database=CFG["MYSQL_DB"], port=CFG["MYSQL_PORT"], connection_timeout=10, use_pure=True
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
                                                    cursor.execute(
                                                        """
                                                        INSERT INTO apartment_listings_price_changes
                                                        (apartment_listings_id, new_price, time)
                                                        VALUES (%s, %s, %s)
                                                        """,
                                                        (listing_id_db, str(price), change_time)
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

                                    try:
                                        cursor.close()
                                        conn.close()
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
                                    status_win.after(0, lambda: finish_step(idx, auto_continue))

                                except Exception as e:
                                    status_win.after(0, lambda: log_activity(f"❌ Step 5 failed: {e}", "#ff0000"))
                                    status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))

                            threading.Thread(target=db_thread, daemon=True).start()
                        except Exception as e:
                            status_win.after(0, lambda: log_activity(f"❌ Step 5 failed: {e}", "#ff0000"))
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                    
                    def execute_step_6(idx, auto_continue=True):
                        """Step 6: Address Match with API call count and final status update"""
                        try:
                            status_win.after(0, lambda: log_activity("Matching addresses...", "#aaa"))
                            status_win.after(0, lambda: progress_frame.pack(fill="x", padx=10, pady=5))

                            # Register a callback so the Address Match window can notify completion
                            def _on_address_match_done(new_calls: int):
                                try:
                                    status_win.after(0, lambda: log_activity(f"📞 New API calls: {new_calls}", "#3498DB"))
                                    status_win.after(0, lambda: log_activity("✅ Done! (status updated)", "#00ff00"))
                                    status_win.after(0, lambda: set_status_summary(idx, f"🗺️ New API calls: {new_calls} • Status: done", "#2ECC71"))
                                    # Update stats and table Summary (Networks)
                                    try:
                                        job_stats['api_calls'] = int(new_calls or 0)
                                        _update_summary_on_table()
                                    except Exception:
                                        pass
                                    # Explicitly mark address_match as done in queue_websites via API
                                    try:
                                        import requests as _rq
                                        api_url = "http://localhost/queue_step_api.php"
                                        payload = {
                                            'table': 'queue_websites',
                                            'id': job_id,
                                            'step': 'address_match',
                                            'status': 'done',
                                            'message': 'completed',
                                            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                        }
                                        _rq.post(api_url, json=payload, timeout=5)
                                    except Exception as _upd_err:
                                        log_to_file(f"[Address Match] Direct status update failed: {_upd_err}")
                                finally:
                                    status_win.after(0, lambda: progress_frame.pack_forget())
                                    status_win.after(0, lambda: finish_step(idx, auto_continue))

                            try:
                                ADDRESS_MATCH_CALLBACKS[str(job_id)] = _on_address_match_done
                            except Exception:
                                pass

                            # Launch the Address Match UI (user can drive or use Auto-Update inside)
                            self._start_job_step(job_id, table, "address_match")
                            # Do not finish here; wait for callback from the Address Match window
                        except Exception as e:
                            status_win.after(0, lambda: log_activity(f"❌ Step 6 failed: {e}", "#ff0000"))
                            status_win.after(0, lambda: status_labels[idx].config(text=f"{steps[idx]} - Failed ❌", fg="#ff0000"))
                    
                    def finish_step(idx, auto_continue=True):
                        finish_step_timer(idx)
                        status_labels[idx].config(text=f"{steps[idx]} - Success ✅", fg="#00ff00")
                        log_activity(f"{steps[idx]} - DONE\n", "#00ff00")
                        step_completed[idx] = True  # Mark step as completed
                        if auto_continue:
                            run_steps(idx + 1)
                    
                    # Start execution
                    log_activity(f"Job {job_id} - {table}", "#ffaa00")
                    log_activity(f"Automated workflow\n", "#aaa")
                    run_steps(0)
                    return
                
                # Handle Edit button click (column #12)
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
                
                # Handle Link column click - copy to clipboard (column #2)
                if column == "#2":
                    values = self._queue_tree.item(item, "values")
                    if values and len(values) > 1:
                        link = values[1]
                        try:
                            self._root.clipboard_clear()
                            self._root.clipboard_append(link)
                            self._queue_status_label.config(text=f"✓ Copied: {link[:50]}...")
                            log_to_file(f"[Queue] Copied link to clipboard: {link}")
                        except Exception as copy_err:
                            log_to_file(f"[Queue] Failed to copy link: {copy_err}")
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
        
        # Right-click handler for JSON column (#7 = 2.JSON) and Parcel empty-count (#5)
        def safe_tree_right_click(event):
            try:
                # Identify the row and column
                item = self._queue_tree.identify_row(event.y)
                column = self._queue_tree.identify_column(event.x)
                
                table_now = str(self._current_table.get() or '').lower()

                # Case 1: JSON column (#7) → show JSON summary popup
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

                # Case 2: Parcel tab, Empty Parcels column (#5) → open addresses-without-parcels window
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
                        url = f"http://localhost/step5/get_empty_parcels_list.php?metro={quote(metro_name)}&limit={state['limit']}&page={state['page']}"
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
                    
                    # If on Parcel tab, trigger the same path as the Refresh button (with loader)
                    if str(current_table).lower() == 'parcel':
                        def _do_refresh():
                            try:
                                if hasattr(self, '_trigger_parcel_refresh'):
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
                        api_url = "http://localhost/step5/get_major_metros.php?only=names"
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
                            values = ["All"] + filtered_api
                            self._metro_combo['values'] = values
                            # Ensure current selection is valid
                            current = self._selected_metro.get()
                            if current not in values:
                                self._selected_metro.set("All")
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
                import threading
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
            # Prevent multiple simultaneous refreshes
            if hasattr(self, '_refresh_in_progress') and self._refresh_in_progress:
                log_to_file("[Queue] Refresh already in progress, skipping...")
                return
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
                # Special handling for Parcel tab: load major_metros with parcel_link via API
                try:
                    api_url = "http://localhost/step5/get_parcel_metros.php?limit=500"
                    if selected_metro and selected_metro != "All":
                        api_url += f"&metro={requests.utils.quote(selected_metro)}"
                    
                    log_to_file(f"[Parcel] Metro filter: '{selected_metro}' | Calling API: {api_url}")
                    r = requests.get(api_url, timeout=10)
                    if r.status_code == 200:
                        data = r.json()
                        log_to_file(f"[Parcel] API response keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}")
                        if isinstance(data, dict) and data.get('ok'):
                            metros = data.get('rows', [])
                            log_to_file(f"[Parcel] API returned {len(metros)} metros: {[m.get('metro_name') for m in metros]}")
                            
                            # Get empty parcels count for the selected metro (or ALL)
                            empty_count = 0
                            if selected_metro and selected_metro != "All":
                                try:
                                    count_url = f"http://localhost/step5/get_empty_parcels_count.php?metro={requests.utils.quote(selected_metro)}"
                                    log_to_file(f"[Parcel] Fetching empty count: {count_url}")
                                    count_resp = requests.get(count_url, timeout=10)
                                    if count_resp.status_code == 200:
                                        count_data = count_resp.json()
                                        if count_data.get('ok'):
                                            empty_count = count_data.get('empty_count', 0)
                                            log_to_file(f"[Parcel] Empty parcels count: {empty_count}")
                                except Exception as count_err:
                                    log_to_file(f"[Parcel] Failed to get empty count: {count_err}")
                            else:
                                # All metros: try to fetch global empty count
                                try:
                                    count_url = "http://localhost/step5/get_empty_parcels_count.php"
                                    log_to_file(f"[Parcel] Fetching global empty count: {count_url}")
                                    count_resp = requests.get(count_url, timeout=10)
                                    if count_resp.status_code == 200:
                                        count_data = count_resp.json()
                                        if count_data.get('ok'):
                                            empty_count = count_data.get('empty_count', 0)
                                            log_to_file(f"[Parcel] Global empty parcels count: {empty_count}")
                                        else:
                                            raise RuntimeError("Global count response not ok")
                                    else:
                                        raise RuntimeError(f"HTTP {count_resp.status_code}")
                                except Exception as count_err:
                                    log_to_file(f"[Parcel] Failed to get global empty count: {count_err}; falling back to per-metro sum")
                                    # Fallback: sum per-metro counts (small N ~6)
                                    try:
                                        majors_url = "http://localhost/step5/get_major_metros.php?only=names"
                                        mj_resp = requests.get(majors_url, timeout=8)
                                        names = []
                                        if mj_resp.status_code == 200:
                                            mj = mj_resp.json()
                                            if isinstance(mj, dict) and isinstance(mj.get('names'), list):
                                                names = [str(x).strip() for x in mj.get('names') if x]
                                        total = 0
                                        for nm in names:
                                            try:
                                                u = f"http://localhost/step5/get_empty_parcels_count.php?metro={requests.utils.quote(nm)}"
                                                cr = requests.get(u, timeout=6)
                                                if cr.status_code == 200:
                                                    cd = cr.json()
                                                    if cd.get('ok'):
                                                        total += int(cd.get('empty_count', 0) or 0)
                                            except Exception:
                                                pass
                                        empty_count = total
                                        log_to_file(f"[Parcel] Global empty parcels (summed): {empty_count}")
                                    except Exception as sum_err:
                                        log_to_file(f"[Parcel] Per-metro sum failed: {sum_err}")
                            parcel_empty_count = empty_count
                            
                            # Build rows: fetch per-metro counts when selected_metro = "All"
                            rows = []
                            per_metro_counts = {}
                            
                            # If "All" selected, fetch individual counts for each metro
                            if selected_metro == "All" or not selected_metro:
                                try:
                                    for m in metros:
                                        metro_nm = m.get('metro_name')
                                        if metro_nm:
                                            try:
                                                count_url = f"http://localhost/step5/get_empty_parcels_count.php?metro={requests.utils.quote(metro_nm)}"
                                                cr = requests.get(count_url, timeout=6)
                                                if cr.status_code == 200:
                                                    cd = cr.json()
                                                    if cd.get('ok'):
                                                        per_metro_counts[metro_nm] = int(cd.get('empty_count', 0) or 0)
                                                        log_to_file(f"[Parcel] {metro_nm}: {per_metro_counts[metro_nm]} empty parcels")
                                            except Exception as _pc_err:
                                                log_to_file(f"[Parcel] Failed to get count for {metro_nm}: {_pc_err}")
                                except Exception as _all_err:
                                    log_to_file(f"[Parcel] Per-metro count fetch failed: {_all_err}")
                            
                            for m in metros:
                                county = (m.get('county_name') or '').strip()
                                metro_nm = m.get('metro_name')
                                metro_id = m.get('id')
                                # Skip if metro name or id is empty
                                if not metro_nm or not metro_id:
                                    continue
                                # Get total address count from API response
                                total_addresses = m.get('address_count', 0)
                                # Use per-metro empty count if available; when filtering a single metro, use fetched empty_count
                                empty_count_val = per_metro_counts.get(
                                    metro_nm,
                                    empty_count if (selected_metro and selected_metro != "All" and metro_nm == selected_metro) else ''
                                )
                                rows.append({
                                    'id': metro_id,
                                    'link': m.get('parcel_link'),
                                    'county_name': county,
                                    'metro_name': metro_nm,
                                    'total_addresses': total_addresses,
                                    'empty_parcels': empty_count_val,
                                    # placeholders to fit existing rendering logic
                                    'run_interval_minutes': 0,
                                    'processed_at': None,
                                    'steps': {}
                                })

                            # TOTAL row removed - no longer showing summary
                            
                            custom_source = 'parcel'
                            if not silent:
                                count_msg = f" ({empty_count} empty parcels)" if selected_metro and selected_metro != "All" else ""
                                log_to_file(f"[Parcel] Loaded {len(rows)} metros with parcel links{count_msg}")
                        else:
                            error_occurred = True
                            error_msg = f"Parcel API returned error: {data.get('error', 'unknown')}"
                            log_to_file(f"[Parcel] {error_msg}")
                    else:
                        error_occurred = True
                        error_msg = f"Parcel API failed: HTTP {r.status_code}"
                        log_to_file(f"[Parcel] {error_msg}")
                except Exception as api_err:
                    error_occurred = True
                    error_msg = f"Parcel load failed: {str(api_err)[:80]}"
                    log_to_file(f"[Parcel] {error_msg}")
                    import traceback
                    log_to_file(f"[Parcel] Traceback: {traceback.format_exc()}")
            elif str(current_table).lower() == 'queue_websites':
                # Special handling for Websites tab: call API to list google_places with non-empty Website
                try:
                    api_url = "http://localhost/step5/get_websites.php?limit=200"
                    if not silent:
                        log_to_file(f"[Websites] Calling API: {api_url}")
                    resp = requests.get(api_url, timeout=10)
                    if resp.status_code == 200:
                        try:
                            data = resp.json()
                        except Exception as je:
                            snippet = resp.text[:300] if hasattr(resp, 'text') else '<no text>'
                            raise RuntimeError(f"Invalid JSON from Websites API: {je}. Snippet: {snippet}")
                        if data.get('ok'):
                            gps = data.get('websites', [])
                            rows = []
                            for gp in gps:
                                rows.append({
                                    'id': gp.get('id'),
                                    'link': gp.get('Website') or '',
                                    'name': gp.get('Name') or '',
                                    'run_interval_minutes': 0,
                                    'processed_at': None,
                                    'steps': {}
                                })
                            custom_source = 'websites'
                            if not silent:
                                log_to_file(f"[Websites] Loaded {len(rows)} websites via API")
                        else:
                            raise RuntimeError(f"Websites API error: {data.get('error', 'Unknown error')}")
                    else:
                        raise RuntimeError(f"Websites API HTTP {resp.status_code}")
                except Exception as api_err:
                    error_occurred = True
                    error_msg = f"Websites load failed: {str(api_err)[:200]}"
                    log_to_file(f"[Websites] {error_msg}")
            elif str(current_table).lower() == 'accounts':
                        # Special handling for Accounts tab: list accounts via API with optional search filter
                        try:
                            api_url = "http://localhost/step5/get_accounts.php"
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
                            api_url = "http://localhost/step5/get_code_cities.php?limit=500"
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
                            api_url = "http://localhost/step5/get_911_cities.php?limit=500"
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
                # Fetch from API instead of direct MySQL
                # Special rule: Networks tab should show queue_websites with status=queued
                api_table = current_table
                status_used = current_status
                if str(current_table).lower() in ("listing_networks", "queue_networks", "networks"):
                api_table = "queue_websites"
                status_used = "queued"
                custom_source = 'networks'
                api_url = f"https://api.trustyhousing.com/manual_upload/queue_website_api.php?table={api_table}&status={status_used}&limit=100"
                if not silent:
                log_to_file(f"[Queue] Fetching from API: {api_url}")
                print(f"[Queue] Fetching {status} from {table} via API")
                        
                response = requests.get(api_url, timeout=30)
                response.raise_for_status()  # Raise error for bad status codes
                        
                data = response.json()
                if not silent:
                log_to_file(f"[Queue] API response received, status={response.status_code}")
                print(f"[Queue] API response: {response.status_code}")
                        
                # Extract rows from API response
                if isinstance(data, dict):
                rows = data.get('data', []) or data.get('rows', []) or []
                # Fallbacks for status-scoped payloads (e.g., { queued: [...], running: [...] } or { data: { queued: [...] } })
                if (not rows) and isinstance(data.get('data'), dict):
                try:
                rows = data['data'].get(status, []) or []
                except Exception:
                rows = []
                if (not rows) and status and isinstance(data.get(status), list):
                rows = data.get(status) or []
                # Networks-specific: common API shape with top-level status buckets
                if (not rows) and str(current_table).lower() in ("listing_networks", "queue_networks", "networks"):
                try:
                # Look for status buckets at top-level
                status_buckets = {}
                for _k, _v in data.items():
                if isinstance(_v, list) and _v and isinstance(_v[0], dict):
                lk = str(_k).lower()
                if lk in ("queued", "queue", "running", "done", "error"):
                status_buckets[lk] = _v
                # If we found buckets, pick by current status; else try 'queue' for 'queued'
                if status_buckets:
                wanted = str(status or "").lower()
                if wanted in status_buckets:
                rows = status_buckets[wanted]
                elif wanted == "queued" and "queue" in status_buckets:
                rows = status_buckets["queue"]
                else:
                # As a last resort, merge all buckets to show something
                merged = []
                for _arr in status_buckets.values():
                merged.extend(_arr)
                rows = merged
                if not silent:
                log_to_file(f"[Networks] Parsed rows from status buckets: {len(rows)}")
                # Also check nested under data.data
                elif isinstance(data.get('data'), dict):
                nested = data['data']
                status_buckets = {}
                for _k, _v in nested.items():
                if isinstance(_v, list) and _v and isinstance(_v[0], dict):
                lk = str(_k).lower()
                if lk in ("queued", "queue", "running", "done", "error"):
                status_buckets[lk] = _v
                if status_buckets:
                wanted = str(status or "").lower()
                if wanted in status_buckets:
                rows = status_buckets[wanted]
                elif wanted == "queued" and "queue" in status_buckets:
                rows = status_buckets["queue"]
                else:
                rows = next(iter(status_buckets.values()))
                if not silent:
                log_to_file(f"[Networks] Parsed rows from nested buckets: {len(rows)}")
                except Exception as _net_parse_err:
                if not silent:
                log_to_file(f"[Networks] Bucket parse failed: {_net_parse_err}")
                # Heuristic: if any top-level key holds a list of dicts, assume it's the row set
                if not rows:
                try:
                for _k, _v in data.items():
                if isinstance(_v, list) and _v and isinstance(_v[0], dict):
                rows = _v
                if not silent:
                log_to_file(f"[Queue] Heuristic rows found under key '{_k}'")
                break
                except Exception:
                pass
                if 'error' in data:
                raise Exception(f"API error: {data['error']}")
                elif isinstance(data, list):
                rows = data
                else:
                rows = []
                # Optional fallback: if status-scoped fetch yields 0, fetch unfiltered and filter client-side
                if (not rows) and status_used in ("queued", "running", "done", "error"):
                try:
                fallback_url = f"https://api.trustyhousing.com/manual_upload/queue_website_api.php?table={api_table}&limit=200"
                if not silent:
                log_to_file(f"[Queue] Fallback fetch (no status) for {api_table}: {fallback_url}")
                fb_resp = requests.get(fallback_url, timeout=30)
                fb_resp.raise_for_status()
                fb_data = fb_resp.json()
                fb_rows = []
                if isinstance(fb_data, dict):
                fb_rows = fb_data.get('data', []) or fb_data.get('rows', []) or []
                if (not fb_rows) and isinstance(fb_data.get('data'), dict):
                # If the unfiltered response still nests by status
                try:
                nested = fb_data['data']
                if isinstance(nested, dict):
                fb_rows = nested.get(status_used, []) or []
                except Exception:
                pass
                # As a last resort, pick the first list-of-dicts value
                if not fb_rows:
                for _k, _v in fb_data.items():
                if isinstance(_v, list) and _v and isinstance(_v[0], dict):
                fb_rows = _v
                break
                # Hide loader and enable combobox
                try:
                _metro_loading_stop()
                except Exception:
                pass
                elif isinstance(fb_data, list):
                fb_rows = fb_data
                # If rows have no clear 'status' key, don't throw them away—prefer to show
                def _row_status(x):
                if not isinstance(x, dict):
                return ""
                for _k in ("status", "queue_status", "state"):
                if _k in x and isinstance(x[_k], str):
                return x[_k].lower()
                return ""
                statuses_present = {_row_status(r) for r in fb_rows}
                if any(s in ("queued", "running", "done", "error") for s in statuses_present):
                rows = [r for r in fb_rows if _row_status(r) == status_used]
                else:
                rows = fb_rows
                if not silent:
                log_to_file(f"[Queue] Fallback provided {len(rows)} '{status_used}' rows after client-side filter")
                except Exception as _fb_err:
                if not silent:
                log_to_file(f"[Queue] Fallback fetch failed: {_fb_err}")

                # Log keys to help diagnose unexpected API shapes
                log_to_file(f"[Queue] No rows extracted. Top-level keys: {list(data.keys())}")
                except Exception:
                pass
                        
                if not silent:
                log_to_file(f"[Queue] Fetched {len(rows)} rows from API (table={api_table}, status={status_used})")
                print(f"[Queue] Fetched {len(rows)} rows")

                    
            try:
                # ...existing code...
            except requests.exceptions.Timeout as e:
                error_occurred = True
                error_msg = "API timeout (30s)"
                log_to_file(f"[Queue] {error_msg}: {e}")
                print(f"[Queue] {error_msg}: {e}")
            except requests.exceptions.RequestException as e:
                error_occurred = True
                error_msg = f"API request failed: {str(e)[:40]}"
                log_to_file(f"[Queue] {error_msg}")
                log_exception("API request error")
                print(f"[Queue] {error_msg}")
            except Exception as e:
                error_occurred = True
                error_msg = f"Fetch failed: {str(e)[:60]}"
                log_to_file(f"[Queue] {error_msg}")
                log_exception("Background fetch error")
                print(f"[Queue] {error_msg}")
            finally:
                # Always reset the lock
                self._refresh_in_progress = False
                # Hide loading indicator
                if hasattr(self, '_hide_loading'):
                        self._root.after(0, self._hide_loading)
                    if not silent:
                        log_to_file("[Queue] Background fetch completed, lock released")
                    
                    # Update UI on main thread with results or error
                    def _update_ui():
                        try:
                            if error_occurred:
                                self._queue_status_label.config(text=error_msg)
                                return
                            
                            if not silent:
                                log_to_file(f"[Queue] Updating UI with {len(rows)} rows")
                                print(f"[Queue] Updating UI with {len(rows)} rows")
                            
                            # Use captured values (already have table and status from outer scope)
                            
                            # Adjust columns per current table before inserting
                            try:
                                if hasattr(self, '_set_queue_columns_for_table'):
                                    self._set_queue_columns_for_table(table, custom_source)
                            except Exception as _colset_err:
                                log_to_file(f"[Queue] Failed to set columns: {_colset_err}")

                            # Clear existing items
                            for item in self._queue_tree.get_children():
                                self._queue_tree.delete(item)
                            
                            if not rows:
                                # Avoid referencing undefined variables for custom sources
                                if str(current_table).lower() == 'parcel':
                                    msg = "No metros with parcel links"
                                elif custom_source == 'websites':
                                    msg = "No websites found"
                                elif custom_source == 'accounts':
                                    msg = "No accounts found"
                                elif custom_source in ('code', '911'):
                                    msg = f"No {str(current_table).lower()} cities found"
                                else:
                                    # Fallback generic message
                                    msg = f"No items"
                                self._queue_status_label.config(text=msg)
                                if not silent:
                                    log_to_file(f"[Queue] {msg}")
                                    print(f"[Queue] {msg}")
                                return
                            
                            count = 0
                            for r in rows:
                                try:
                                    job_id = r.get("id", "")
                                    # For parcel table, don't truncate link to show full URL
                                    max_link_len = 260 if str(current_table).lower() == 'parcel' else 30
                                    link = str(
                                        r.get("link")
                                        or r.get("url")
                                        or r.get("website")
                                        or r.get("network_url")
                                        or ""
                                    )[:max_link_len]
                                    row_status = str(r.get("status") or "").lower()
                                    
                                    # Cache the full job data for later use
                                    self._job_data_cache[str(job_id)] = r
                                    
                                    # Get step status from the job record
                                    # Assuming steps are stored in separate columns or a JSON field
                                    step_data = r.get("steps", {})
                                    if isinstance(step_data, str):
                                        try:
                                            step_data = json.loads(step_data)
                                        except:
                                            step_data = {}
                                    
                                    # Helper to get step display
                                    def get_step_display(step_name):
                                        if isinstance(step_data, dict) and step_data.get(step_name) == "done":
                                            return "✓"
                                        elif isinstance(step_data, dict) and step_data.get(step_name) == "running":
                                            return "⏳"
                                        elif isinstance(step_data, dict) and step_data.get(step_name) == "error":
                                            return "✗"
                                        else:
                                            return "▶ Start"

                                    # Build step columns
                                    step1 = get_step_display("capture_html")
                                    step2 = get_step_display("create_json")
                                    step3 = get_step_display("manual_match")
                                    step4 = get_step_display("process_db")
                                    step5 = get_step_display("insert_db")
                                    step6 = get_step_display("address_match")

                                    # If today's networks_{id}.html exists OR any date's file exists in Captures, override step1 to show a check with date
                                    # Only perform file presence checks for default sources (skip for Networks/Websites/Accounts/Parcel custom sources)
                                    if not custom_source:
                                        try:
                                            from datetime import datetime as _dt
                                            date_str = _dt.now().strftime("%Y-%m-%d")
                                            # Determine prefix based on current table
                                            original_table = str(current_table).lower()
                                            prefix = original_table
                                            if original_table in ("queue_websites", "listing_websites", "websites"):
                                                prefix = "networks"
                                            else:
                                                if "_" in original_table:
                                                    prefix = original_table.split("_")[-1]
                                            
                                            # Check for HTML file (Step 1)
                                            html_path = BASE_DIR / date_str / f"{prefix}_{job_id}.html"
                                            html_exists = False
                                            if html_path.exists():
                                                # Today's file exists - show checkmark with today's date
                                                step1 = f"✓ {date_str}"
