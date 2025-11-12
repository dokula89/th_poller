def claim_queued_rows(conn, table: str, max_rows: int) -> List[Dict[str, Any]]:
    max_retries = 3
    base_delay = 1.0
    
    for attempt in range(max_retries):
        cur = conn.cursor(dictionary=True)
        try:
            # Start transaction with a shorter lock timeout for claim operation
            cur.execute("SET SESSION innodb_lock_wait_timeout = 30")  # Shorter timeout for claims
            
            # First check if any job is already running
            cur.execute("SELECT COUNT(*) as cnt FROM `{}` WHERE status='running'".format(table))
            row = cur.fetchone()
            if row and row["cnt"] > 0:
                conn.commit()
                cur.close()
                return []  # Don't claim new jobs if one is already running
            
            # If no job is running, try to claim one
            cur.execute(
                f"""
                SELECT id
                FROM `{table}`
                WHERE status='queued'
                ORDER BY priority DESC, id ASC
                LIMIT %s
                FOR UPDATE SKIP LOCKED  -- Skip locked rows instead of waiting
                """, (max_rows,))
            
            ids = [r["id"] for r in cur.fetchall()]
            
            if not ids:
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
            
            placeholders = ",".join(["%s"] * len(ids))
            cur.execute(
                f"""
                UPDATE `{table}`
                SET status='running',
                    attempts=attempts+1,
                    updated_at=NOW()
                WHERE id IN ({placeholders}) AND status='queued'
                """, ids)

            cur.execute(
                f"""
                SELECT id, link, the_css, priority, attempts, source_table, source_id, run_interval_minutes
                FROM `{table}`
                WHERE id IN ({placeholders})
                ORDER BY priority DESC, id ASC
                """, ids)
            
            rows = cur.fetchall()
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