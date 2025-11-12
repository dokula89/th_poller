#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time, signal, threading, os, uuid
from typing import Optional, Dict, Any, List
from contextlib import contextmanager

# Local modules
from config_utils import (
    CFG, BASE_DIR, GLOBAL_JSON_PATH, IMAGES_DIR,
    hud_start, hud_run_mainloop_blocking, hud_push, hud_counts, hud_is_paused, hud_is_auto_run_enabled,
    hud_loader_show, hud_loader_update, hud_loader_hide,
    ensure_dir, log_file,
    # SFTP helpers and config for uploads
    sftp_upload_dir, SFTP_ENABLED, SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS,
    REMOTE_IMAGES_PARENT,
)
from config_core import php_url
from config_utils import ensure_session_before_hud
from config_helpers import launch_manual_browser
from parser_core import run_capture_and_extract, REQUEUE_EMPTY_PARSE
from datetime import datetime
import requests
from urllib.parse import quote_plus

# MySQL
try:
    import mysql.connector as mysql
    from mysql.connector import pooling
except ImportError as e:
    raise SystemExit("Please install: pip install mysql-connector-python") from e

# Configure the connection pool
POOL_NAME = "th_poller_pool"
POOL_SIZE = 2  # Reduced from 5 for faster startup - will expand as needed

db_config = {
    "host": CFG["MYSQL_HOST"],
    "port": CFG["MYSQL_PORT"],
    "user": CFG["MYSQL_USER"],
    "password": CFG["MYSQL_PASSWORD"],
    "database": CFG["MYSQL_DB"],
    "pool_name": POOL_NAME,
    "pool_size": POOL_SIZE,
    "pool_reset_session": True,  # Reset session state on get
    "use_pure": True,
    "autocommit": False,
    "connect_timeout": 5,  # Reduced from 10 - fail faster
    "connection_timeout": 5,  # Reduced from 10 - fail faster
}

# Telegram
from config_utils import notify_telegram_error

shutdown_flag = False

# ---------- DB helpers ----------
# Connection pool (lazy-init so HUD can appear first)
connection_pool = None

def init_connection_pool(retries=3):
    """Initialize connection pool with retry logic."""
    global connection_pool
    if connection_pool is not None:
        return
    
    for attempt in range(retries):
        try:
            connection_pool = mysql.pooling.MySQLConnectionPool(**db_config)
            log_file(f"MySQL connection pool initialized with {POOL_SIZE} connections")
            return
        except Exception as e:
            # Only log on last attempt to reduce noise
            if attempt == retries - 1:
                log_file(f"Could not connect to database after {retries} attempts. Queue viewer will work, but job processing disabled.")
            else:
                # Silently retry
                time.sleep(1)  # Shorter wait
    
    # Don't raise - allow the app to start without DB
    return

@contextmanager
def get_db_connection():
    """Context manager for getting a connection from the pool with retry logic."""
    conn = None
    max_retries = 2
    
    for attempt in range(max_retries):
        try:
            if connection_pool is None:
                init_connection_pool()
                if connection_pool is None:
                    raise Exception("Connection pool not initialized")
            
            conn = connection_pool.get_connection()
            # Test connection is alive
            conn.ping(reconnect=True, attempts=2, delay=1)
            
            # Set session-level lock wait timeout
            cur = conn.cursor()
            try:
                cur.execute(f"SET SESSION innodb_lock_wait_timeout = {CFG['MYSQL_LOCK_TIMEOUT']}")
                conn.commit()
            finally:
                if cur:
                    try: cur.close()
                    except: pass
            
            # Success - yield the connection
            yield conn
            return  # Exit after successful use
            
        except Exception as e:
            log_file(f"Error getting connection (attempt {attempt + 1}/{max_retries}): {e}")
            if conn:
                try: conn.close()
                except: pass
                conn = None
            
            if attempt < max_retries - 1:
                time.sleep(1)  # Brief pause before retry
            else:
                # Final attempt failed
                raise
        finally:
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass

def db_connect():
    """Legacy connection function - uses the pool"""
    if connection_pool is None:
        init_connection_pool()
    return connection_pool.get_connection()

def status_counts(conn, table: str) -> Dict[str, int]:
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(f"SELECT status, COUNT(*) c FROM `{table}` GROUP BY status")
        rows = cur.fetchall()
        return {r["status"]: int(r["c"]) for r in rows}
    finally:
        cur.close()

def any_queued(conn, table: str) -> bool:
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT COUNT(*) FROM `{table}` WHERE status='queued'")
        (n,) = cur.fetchone()
        return int(n or 0) > 0
    finally:
        cur.close()

def reclaim_stale_running(conn, table: str, minutes: int):
    if minutes <= 0:
        return
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries):
        cur = conn.cursor()
        try:
            cur.execute(
                f"""
                UPDATE `{table}`
                SET status='queued', updated_at=NOW()
                WHERE status='running' AND updated_at < NOW() - INTERVAL %s MINUTE
                """, (minutes,)
            )
            changed = cur.rowcount
            conn.commit()
            if changed:
                log_file(f"Reclaimed {changed} stale 'running' rows.")
            return  # Success, exit function
        except Exception as e:
            conn.rollback()
            cur.close()
            
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                log_file(f"Reclaim attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                time.sleep(delay)
            else:
                # Log error only on final attempt
                log_file(f"Reclaim error (ignored after {max_retries} attempts): {e}")
                notify_telegram_error(title="Reclaim stale-running error", 
                                   details=f"Failed after {max_retries} attempts: {e}", 
                                   context=f"table={table}")
        finally:
            if cur:
                try: cur.close()
                except: pass

def ensure_run_interval_column(conn, table: str):
    cur = conn.cursor()
    try:
        cur.execute(
            """
            SELECT COUNT(*)
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s
              AND TABLE_NAME   = %s
              AND COLUMN_NAME  = 'run_interval_minutes'
            """,
            (CFG["MYSQL_DB"], table)
        )
        exists = (cur.fetchone() or [0])[0] > 0
        if exists:
            conn.commit()
            return
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `run_interval_minutes` INT NULL")
        conn.commit()
        log_file(f"Added `{table}.run_interval_minutes` column.")
    except mysql.Error as e:
        conn.rollback()
        if "Duplicate column name" in str(e):
            log_file("Column run_interval_minutes already exists (race).")
        else:
            log_file(f"Could not ensure run_interval_minutes column: {e}")
            notify_telegram_error(title="ALTER TABLE failed", details=str(e), context=table)
            raise
    finally:
        cur.close()

def auto_requeue_due_rows(conn, table: str):
    cur = conn.cursor()
    try:
        cur.execute(
            f"""
            UPDATE `{table}`
            SET status='queued', updated_at=NOW()
            WHERE run_interval_minutes IS NOT NULL
              AND run_interval_minutes > 0
              AND status IN ('done','error')
              AND TIMESTAMPDIFF(
                    MINUTE,
                    COALESCE(processed_at, updated_at, created_at),
                    NOW()
                  ) >= run_interval_minutes
            """
        )
        changed = cur.rowcount
        conn.commit()
        if changed:
            log_file(f"Auto re-queued {changed} due rows based on run_interval_minutes.")
    except Exception as e:
        conn.rollback()
        log_file(f"Auto requeue error (ignored this cycle): {e}")
        notify_telegram_error(title="Auto requeue error", details=str(e), context=f"table={table}")
    finally:
        cur.close()

def claim_queued_rows(conn, table: str, max_rows: int) -> List[Dict[str, Any]]:
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries):
        cur = conn.cursor(dictionary=True)
        try:
            # Start transaction with a shorter lock timeout for claim operation
            cur.execute("SET SESSION innodb_lock_wait_timeout = 30")  # Shorter timeout for claims
            
            # Acquire a short user-level lock to serialize claim operations across workers
            lock_name = f"{table}_claim_lock"
            cur.execute("SELECT GET_LOCK(%s, %s)", (lock_name, 5))
            got_lock_row = cur.fetchone()
            got_lock = False
            if got_lock_row:
                # Value can be 1 (success), 0 (timeout), or NULL (error). Extract first value.
                got_lock = list(got_lock_row.values())[0] == 1

            if not got_lock:
                # Could not obtain the claim lock quickly — back off and retry
                conn.commit()
                cur.close()
                time.sleep(0.5)
                continue

            # Within the lock, do not claim if something is already running
            cur.execute(f"SELECT COUNT(*) AS running_count FROM `{table}` WHERE status='running'")
            row = cur.fetchone()
            running_count = int(row.get("running_count", 0) if row else 0)
            if running_count > 0:
                # Release the user-level lock and return nothing
                try:
                    cur.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                    try:
                        _ = cur.fetchone()  # consume result to avoid 'Unread result found'
                    except Exception:
                        pass
                except Exception:
                    pass
                conn.commit()
                cur.close()
                try:
                    counts = status_counts(conn, table)
                    hud_counts(counts.get('queued',0), counts.get('running',0), counts.get('done',0), counts.get('error',0))
                except Exception:
                    pass
                return []

            # Select one queued id to claim
            cur.execute(
                f"""
                SELECT id
                FROM `{table}`
                WHERE status='queued'
                ORDER BY priority DESC, id ASC
                LIMIT 1
                FOR UPDATE SKIP LOCKED
                """
            )
            ids = [r["id"] for r in cur.fetchall()]
            
            if not ids:
                # Release the lock before returning
                try:
                    cur.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                    try:
                        _ = cur.fetchone()  # consume result
                    except Exception:
                        pass
                except Exception:
                    pass
                conn.commit()
                cur.close()
                try:
                    counts = status_counts(conn, table)
                    hud_counts(counts.get('queued',0), counts.get('running',0), counts.get('done',0), counts.get('error',0))
                except Exception:
                    pass
                return []

            # Reset lock timeout to normal value for remaining operations
            cur.execute(f"SET SESSION innodb_lock_wait_timeout = {CFG['MYSQL_LOCK_TIMEOUT']}")

            # Claim the selected id (do not touch updated_at; increment attempts)
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(
                f"""
                UPDATE `{table}`
                SET status='running',
                    attempts=attempts+1
                WHERE id IN ({placeholders})
                  AND status='queued'
                """, ids
            )

            cur.execute(
                f"""
                SELECT id, link, the_css, priority, attempts, source_table, source_id, run_interval_minutes
                FROM `{table}`
                WHERE id IN ({placeholders})
                ORDER BY priority DESC, id ASC
                """, ids
            )
            rows = cur.fetchall()
            # Release the claim lock now that update/select is complete
            try:
                cur.execute("SELECT RELEASE_LOCK(%s)", (lock_name,))
                try:
                    _ = cur.fetchone()  # consume result
                except Exception:
                    pass
            except Exception:
                pass
            conn.commit()
            return rows
            
        except Exception as e:
            conn.rollback()
            cur.close()
            
            if attempt < max_retries - 1:  # Don't sleep on last attempt
                delay = base_delay * (2 ** attempt)  # Exponential backoff
                log_file(f"Claim attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                time.sleep(delay)
            else:
                # Log error only on final attempt
                log_file(f"Claim error (failed after {max_retries} attempts): {e}")
                notify_telegram_error(title="Claim queued rows failed", 
                                   details=f"Failed after {max_retries} attempts: {e}", 
                                   context=f"table={table}")
                raise
        finally:
            if cur:
                try: cur.close()
                except: pass
    
    return []  # Should only reach here if all retries failed and didn't raise

def update_job_status(conn, job_id: int, status: str,
                      output_json_path: Optional[str] = None,
                      error_msg: Optional[str] = None):
    cur = conn.cursor()
    table = CFG["TABLE_NAME"]
    try:
        cur.execute(
            f"""
            UPDATE `{table}`
            SET status=%s,
                output_json_path = COALESCE(%s, output_json_path),
                last_error = %s,
                processed_at = CASE WHEN %s IN ('done','error') THEN NOW() ELSE processed_at END,
                updated_at = CASE WHEN %s = 'done' THEN NOW() ELSE updated_at END
            WHERE id=%s
            """,
            (status, output_json_path, error_msg, status, status, job_id)
        )
        conn.commit()
        hud_push(f"Job {job_id}: {status}")
        try:
            counts = status_counts(conn, table)
            hud_counts(counts.get('queued',0), counts.get('running',0), counts.get('done',0), counts.get('error',0))
        except Exception:
            pass
    except Exception as e:
        conn.rollback()
        notify_telegram_error(title="Update job status failed", details=str(e), context=f"job_id={job_id} status={status}")
        raise
    finally:
        cur.close()

# ---------- PHP bridge: trigger process_html_with_openai.php ----------
def _today_dir_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def run_php_processor_for_html(source_id: Optional[int], html_path: Optional[str] = None,
                               method: str = "local", model: str = "gpt-4o-mini",
                               timeout_sec: int = 600) -> Optional[Dict[str, Any]]:
    """
    Fire the PHP processor for a specific HTML file in headless mode and stream status to the HUD.
    Uses headless=1 mode which processes immediately and returns the result.
    Returns the final status JSON (dict) on success, or None on failure/timeout.
    """
    try:
        hud_push(f"[PHP] Starting processor for source_id={source_id}")
        # Determine HTML path if not provided
        if not html_path:
            if source_id is None:
                hud_push("[PHP] Skipping: no source_id and no html_path provided")
                return None
            html_path = str(BASE_DIR / _today_dir_str() / f"networks_{int(source_id)}.html")

        if not os.path.isfile(html_path):
            hud_push(f"[PHP] HTML not found: {html_path}")
            return None

        hud_push(f"[PHP] Processing {os.path.basename(html_path)}...")
        base_url = php_url("process_html_with_openai.php")

        # Use headless mode - processes immediately and returns result
        params = {
            "process": "1",
            "headless": "1",
            "file": html_path,
            "method": method,
            "model": model,
        }
        
        hud_push(f"[PHP] Running headless extraction...")
        try:
            # Headless mode can take a long time, use extended timeout
            r = requests.get(base_url, params=params, timeout=timeout_sec)
        except requests.exceptions.Timeout:
            hud_push(f"[PHP] Timeout after {timeout_sec}s")
            return None
        except Exception as e:
            hud_push(f"[PHP] Request failed: {e}")
            return None
            
        if not r.ok:
            hud_push(f"[PHP] HTTP {r.status_code}")
            return None

        # Parse the JSON response
        try:
            result = r.json()
            # Extract nested result from status
            status = result.get("status", {})
            result_data = status.get("result", {})
            
            listings_count = result_data.get("listingsCount", 0)
            save_path = result_data.get("savePath", "")
            hud_push(f"[PHP] Done — {listings_count} listings extracted")
            
            if save_path:
                hud_push(f"[PHP] JSON: {os.path.basename(save_path)}")
            
            # Report SFTP upload status if present
            sftp_result = result_data.get("sftp", {})
            if sftp_result.get("success"):
                hud_push(f"[PHP] SFTP JSON: OK")
            elif "success" in sftp_result:
                hud_push(f"[PHP] SFTP JSON: Failed")
                
            html_sftp = result_data.get("htmlSftp", {})
            if html_sftp.get("success"):
                hud_push(f"[PHP] SFTP HTML: OK")
            elif "success" in html_sftp:
                hud_push(f"[PHP] SFTP HTML: Failed")
            
            # Download images from HTML file after successful extraction
            if listings_count > 0 and html_path:
                download_images_from_html(html_path, source_id or 1)
                
            return result
        except Exception as e:
            hud_push(f"[PHP] Failed to parse result: {e}")
            return None
    except Exception as e:
        hud_push(f"[PHP] Bridge error: {e}")
        return None

def download_images_from_html(html_path: str, network_id: int) -> None:
    """Extract image URLs from HTML and download them to Captures/images folder, then SFTP-upload the folder."""
    try:
        from bs4 import BeautifulSoup
        hud_push("[Images] Extracting images from HTML…")

        # Read HTML file
        with open(html_path, 'r', encoding='utf-8') as f:
            html_content = f.read()

        soup = BeautifulSoup(html_content, 'html.parser')

        # Find all listing items
        listing_items = soup.find_all('div', class_=lambda x: x and 'listing-item' in x and 'result' in x)
        if not listing_items:
            hud_push("[Images] No listings found in HTML")
            return

        # Ensure images directory exists
        images_dir = IMAGES_DIR
        images_dir.mkdir(parents=True, exist_ok=True)

        downloaded = failed = skipped = 0
        first_filename: Optional[str] = None
        for idx, item in enumerate(listing_items, 1):
            img_tag = item.find('img', class_=lambda x: x and 'listing-item__image' in x)
            if not img_tag:
                skipped += 1
                continue

            # Prefer data-original over src
            img_url = img_tag.get('data-original') or img_tag.get('src')
            if not img_url:
                skipped += 1
                continue

            # If file already exists for this index with any common extension, skip download
            base = f"network_{network_id}_{idx:03d}"
            for_try_exts = ("jpg","jpeg","png","gif","webp")
            existing_path = None
            for ex in for_try_exts:
                cand = images_dir / f"{base}.{ex}"
                if cand.exists():
                    try:
                        if cand.stat().st_size > 0:
                            existing_path = cand
                            break
                    except Exception:
                        pass
            if existing_path is not None:
                skipped += 1
                if not first_filename:
                    first_filename = existing_path.name
                continue

            # Determine extension from URL for new download
            low = img_url.lower()
            if ".png" in low:
                ext = "png"
            elif ".jpeg" in low or ".jpg" in low:
                ext = "jpg"
            elif ".gif" in low:
                ext = "gif"
            elif ".webp" in low:
                ext = "webp"
            else:
                ext = "jpg"

            # network_{network_id}_{result_number}.{ext}
            filename = f"{base}.{ext}"
            save_path = images_dir / filename

            try:
                resp = requests.get(img_url, timeout=15)
                if resp.ok:
                    save_path.write_bytes(resp.content)
                    downloaded += 1
                    if not first_filename:
                        first_filename = filename
                    if downloaded % 25 == 0:
                        hud_push(f"[Images] Downloaded {downloaded}/{len(listing_items)}…")
                else:
                    failed += 1
            except Exception:
                failed += 1
                continue

        hud_push(f"[Images] Complete: {downloaded} downloaded, {failed} failed, {skipped} skipped")

        # Upload the images folder via SFTP
        if SFTP_ENABLED:
            try:
                hud_push("[Images] Uploading images folder to server…")
                # Upload directly into /home/daniel/trustyhousing.com/app/public/img
                ok = sftp_upload_dir(
                    images_dir,
                    SFTP_HOST, SFTP_PORT, SFTP_USER, SFTP_PASS,
                    REMOTE_IMAGES_PARENT,
                    remote_subdir="img"
                )
                hud_push("[Images] SFTP upload OK → /img" if ok else "[Images] SFTP upload failed")
                # Quick public URL check for the first file
                if ok and first_filename:
                    try:
                        public_url = f"https://trustyhousing.com/img/{first_filename}"
                        resp = requests.get(public_url, timeout=10)
                        if resp.status_code == 200:
                            hud_push(f"[Images] Verified public: {public_url}")
                        else:
                            hud_push(f"[Images] Public check HTTP {resp.status_code}: {public_url}")
                    except Exception as ce:
                        hud_push(f"[Images] Public check failed: {ce}")
            except Exception as e:
                hud_push(f"[Images] SFTP error: {e}")
        else:
            hud_push("[Images] SFTP disabled; skipping upload")

    except ImportError:
        hud_push("[Images] Error: BeautifulSoup not installed. Run: pip install beautifulsoup4")
    except Exception as e:
        hud_push(f"[Images] Error: {e}")
def download_images_from_json(json_path: str) -> None:
    """Download images from listings JSON and save to Captures/images folder."""
    try:
        import json
        from pathlib import Path
        
        hud_push("[Images] Starting image download...")
        
        # Read JSON file
        with open(json_path, 'r', encoding='utf-8') as f:
            listings = json.load(f)
        
        if not isinstance(listings, list):
            hud_push(f"[Images] Error: JSON is not a list")
            return
        
        # Ensure images directory exists
        images_dir = BASE_DIR / "Captures" / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        downloaded = 0
        failed = 0
        skipped = 0
        
        for listing in listings:
            result_num = listing.get('result_number', 0)
            network_id = listing.get('network_id', 1)
            img_url = listing.get('img_urls', '')
            
            if not img_url or not isinstance(img_url, str):
                skipped += 1
                continue
            
            # Determine file extension from URL
            ext = 'jpg'
            if '.png' in img_url.lower():
                ext = 'png'
            elif '.jpeg' in img_url.lower() or '.jpg' in img_url.lower():
                ext = 'jpg'
            elif '.gif' in img_url.lower():
                ext = 'gif'
            elif '.webp' in img_url.lower():
                ext = 'webp'
            
            # Generate filename: network_{network_id}_{result_number}.{ext}
            filename = f"network_{network_id}_{result_num:03d}.{ext}"
            save_path = images_dir / filename
            
            # Download image
            try:
                response = requests.get(img_url, timeout=10)
                if response.ok:
                    save_path.write_bytes(response.content)
                    downloaded += 1
                    if downloaded % 25 == 0:
                        hud_push(f"[Images] Downloaded {downloaded}/{len(listings)}...")
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                continue
        
        hud_push(f"[Images] Complete: {downloaded} downloaded, {failed} failed, {skipped} skipped")
        
    except Exception as e:
        hud_push(f"[Images] Error: {e}")


# ---------- Worker loop ----------
def worker_thread():
    table = CFG["TABLE_NAME"]
    backoff = 1.0
    backoff_max = 30.0
    poll_count = 0
    db_available = False

    # Try initial DB setup, but don't block if it fails
    try:
        with get_db_connection() as conn:
            log_file(f"Connected to database. Polling `{table}`…")
            db_available = True
            try:
                counts = status_counts(conn, table)
                hud_counts(counts.get('queued',0), counts.get('running',0), counts.get('done',0), counts.get('error',0))
            except Exception:
                pass
            try:
                ensure_run_interval_column(conn, table)
            except Exception as e:
                log_file(f"Ensure column failed (ignored): {e}")
                notify_telegram_error(title="Ensure column failed", details=str(e), context=table)
    except Exception:
        # Silently continue without DB - user will see the message from init_connection_pool
        hud_push("⚠️ DB unavailable - Queue view only (manual steps work)")
        db_available = False

    while not shutdown_flag:
        # Skip job processing if DB is not available
        if not db_available:
            time.sleep(5)  # Longer sleep when DB unavailable
            continue
            
        try:
            # Get a fresh connection from the pool for each iteration
            with get_db_connection() as conn:
                # 1) Reclaim stale running
                try:
                    reclaim_stale_running(conn, table, CFG["RECLAIM_MINUTES"])
                except Exception as e:
                    log_file(f"Reclaim error (ignored): {e}")
                    notify_telegram_error(title="Reclaim stale-running error", details=str(e), context=f"table={table}")

                # If paused, perform minimal maintenance (counts + due requeue) then idle
                if hud_is_paused():
                    try:
                        counts = status_counts(conn, table)
                        hud_counts(counts.get('queued',0), counts.get('running',0), counts.get('done',0), counts.get('error',0))
                    except Exception:
                        pass
                    try:
                        auto_requeue_due_rows(conn, table)
                    except Exception as e:
                        log_file(f"Auto requeue (paused) failed (ignored): {e}")
                    time.sleep(CFG["POLL_INTERVAL_SEC"])
                    continue

                # Check if auto-run is enabled - if not, only process manually started jobs
                auto_run_enabled = hud_is_auto_run_enabled()
                
                # 2) Claim queued rows (only if auto-run is enabled)
                rows = []
                if auto_run_enabled:
                    rows = claim_queued_rows(conn, table, max_rows=CFG["CLAIM_BATCH_SIZE"])
                    poll_count += 1

                    # If none queued, auto-requeue due rows, then re-claim
                    if not rows:
                        try:
                            if not any_queued(conn, table):
                                auto_requeue_due_rows(conn, table)
                                rows = claim_queued_rows(conn, table, max_rows=CFG["CLAIM_BATCH_SIZE"])
                        except Exception as e:
                            log_file(f"Queued check failed (ignored): {e}")
                else:
                    # Manual mode: Only process jobs that are already marked as 'running'
                    # (these were started via the UI Start button)
                    try:
                        cur = conn.cursor(dictionary=True)
                        cur.execute(f"SELECT * FROM `{table}` WHERE status='running' LIMIT {CFG['CLAIM_BATCH_SIZE']}")
                        rows = cur.fetchall()
                        cur.close()
                        if rows:
                            log_file(f"[Manual Mode] Found {len(rows)} manually started jobs")
                    except Exception as e:
                        log_file(f"Failed to fetch running jobs in manual mode: {e}")
                        rows = []

                # Idle
                if not rows:
                    time.sleep(CFG["POLL_INTERVAL_SEC"])
                    continue

                # Process claims
                any_failures = False
                successful_job_ids: List[int] = []

                for row in rows:
                    while hud_is_paused():
                        time.sleep(0.2)

                    job_id = row["id"]
                    the_css = (row.get("the_css") or "").strip()
                    link = (row.get("link") or "").strip()
                    source_table = row.get("source_table")
                    source_id = row.get("source_id")
                    network_id = row.get("external_id") or row.get("network_id")
                    website = row.get("link") or row.get("listing_url") or row.get("details_link") or row.get("apply_now_link")

                    # Show in HUD status
                    hud_push(f"Job {job_id} | Network: {network_id or '-'} | Site: {website or '-'}")

                    if CFG["REQUIRE_BOTH_FIELDS"] and (not the_css or not link):
                        msg = "Missing the_css or link"
                        log_file(f"Skipping id={job_id}: {msg}")
                        update_job_status(conn, job_id, status="error", error_msg=msg)
                        notify_telegram_error(title="Job skipped / errored (missing field)", details=msg,
                                              context=f"job_id={job_id} link='{link}' css='{the_css}'")
                        any_failures = True
                        continue

                    try:
                        log_file(f"[Worker] About to call run_capture_and_extract for job {job_id}, source_id={source_id}")
                        hud_push(f"[Worker] Starting extraction for job {job_id}")
                        out_json_path = run_capture_and_extract(link, the_css, source_table, source_id, job_id)
                        log_file(f"[Worker] run_capture_and_extract returned: {out_json_path}")
                        hud_push(f"[Worker] Extraction returned: {out_json_path}")
                        if out_json_path == REQUEUE_EMPTY_PARSE:
                            msg = "Parser returned 0 records."
                            log_file(f"Job id={job_id}: {msg} → re-queued (sentinel)")
                            try:
                                update_job_status(conn, job_id, status="queued", error_msg=msg)
                            except Exception as ie:
                                log_file(f"Failed to re-queue job {job_id}: {ie}")
                                notify_telegram_error(title="Re-queue update failed", details=str(ie), context=f"job_id={job_id}")
                            continue

                        update_job_status(conn, job_id, status="done", output_json_path=out_json_path)
                        log_file(f"Job id={job_id} marked done.")
                        successful_job_ids.append(job_id)

                    except Exception as e:
                        err = str(e)
                        any_failures = True
                        log_file(f"[Worker] Exception in job {job_id}: {err}")
                        hud_push(f"[Worker] Job {job_id} ERROR: {err}")
                        update_job_status(conn, job_id, status="error", error_msg=err)
                        log_file(f"Job id={job_id} failed: {err}")
                        notify_telegram_error(title="Job failed", details=err,
                                              context=f"job_id={job_id} link='{link}' css='{the_css}'")

                # Refresh counters after batch
                try:
                    counts = status_counts(conn, table)
                    hud_counts(counts.get('queued',0), counts.get('running',0), counts.get('done',0), counts.get('error',0))
                except Exception:
                    pass

        except mysql.Error as e:
            log_file(f"MySQL error: {e}")
            notify_telegram_error(title="MySQL error", details=str(e), context=f"table={table}")
            time.sleep(min(backoff := (backoff * 2 if backoff < backoff_max else backoff_max), backoff_max))
        except Exception as e:
            log_file(f"Unhandled worker error: {e}")
            notify_telegram_error(title="Unhandled worker error", details=str(e), context="worker_thread loop")
            time.sleep(1.0)

    log_file("Worker stopped cleanly.")
    hud_push("Worker stopped")

def _handle_sig(sig, frame):
    global shutdown_flag
    shutdown_flag = True
    log_file(f"Shutdown signal received ({sig}).")
    notify_telegram_error(title="Shutdown signal received", details=f"signal={sig}", context="main", throttle=False)

def main():
    # Show splash screen during initialization
    from config_utils import SplashScreen
    splash = SplashScreen()
    splash.update_progress(25, "Preparing UI...")
    time.sleep(0.1)

    # Ensure session BEFORE showing HUD; use splash root as parent for login
    try:
        ok = ensure_session_before_hud(splash.root)
    except Exception:
        ok = False
    if not ok:
        try: splash.close()
        except Exception: pass
        return

    # Close splash BEFORE creating the main Tk root to avoid multiple Tk roots on Windows
    try:
        splash.close()
    except Exception:
        pass

    # Build HUD on main thread (no mainloop yet)
    hud_start()
    hud_push("Starting poller (HTTP mode, HUD on main thread).")

    # Worker in background - will initialize DB pool on first use
    t_worker = threading.Thread(target=worker_thread, daemon=True)
    t_worker.start()

    # Tk mainloop blocks here (HUD visible)
    try:
        hud_run_mainloop_blocking()
    except KeyboardInterrupt:
        pass
    finally:
        # Ask worker to stop, then exit
        _handle_sig("KeyboardInterrupt", None)
        try:
            t_worker.join(timeout=2.0)
        except Exception:
            pass

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_sig)
    signal.signal(signal.SIGTERM, _handle_sig)
    main()