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

# Insert DB window

from config_core import *

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
    
    # Find JSON file for this job
    log_to_file(f"[Insert DB] Looking for JSON file for job {job_id}")
    date_str = datetime.now().strftime("%Y-%m-%d")
    json_path = BASE_DIR / date_str / f"networks_{job_id}.json"
    
    log_to_file(f"[Insert DB] Initial path: {json_path}")
    
    # Search all date folders if not found today
    if not json_path.exists():
        log_to_file(f"[Insert DB] File not found at {json_path}, searching other folders...")
        pattern = str(BASE_DIR / "*" / f"networks_{job_id}.json")
        matching = __import__('glob').glob(pattern)
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
                        host=CFG["MYSQL_HOST"],
                        user=CFG["MYSQL_USER"],
                        password=CFG["MYSQL_PASSWORD"],
                        database=CFG["MYSQL_DB"],
                        port=CFG["MYSQL_PORT"],
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
                            
                            # Track in network_daily_stats table for statistics
                            try:
                                # Update or insert today's stats for this network
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
                        log_to_file(f"[Insert DB] network_daily_stats update failed: {stats_err}")

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
                conn.commit()
                ui_append(f"🧹 Marked {deactivated_here} listing(s) inactive for network_{job_id}")
            except Exception as deact_err:
                log_to_file(f"[Insert DB] Network-based deactivation failed for network_id={job_id}: {deact_err}")

            ui_set_stats(inactive=inactive_count)
            ui_set_eta("Done!")
            
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
            api_url = "http://localhost/queue_step_api.php"
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

