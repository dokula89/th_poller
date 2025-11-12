#!/usr/bin/env python3
"""
Database copy script - copies offta database from remote to local MySQL.
Uses Python mysql.connector to avoid authentication issues with mysqldump.
"""
import mysql.connector
import sys
from datetime import datetime

# Source database (remote)
SOURCE = {
    'host': '172.104.206.182',
    'user': 'seattlelisted_usr',
    'password': 'T@5z6^pl}',
    'database': 'offta',
    'port': 3306
}

# Destination database (local)
DEST = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '',
    'database': 'offta',
    'port': 3306
}

def copy_database():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting database copy...")
    print(f"Source: {SOURCE['host']} -> Destination: {DEST['host']}")
    
    # Connect to source
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connecting to source database...")
    try:
        source_conn = mysql.connector.connect(**SOURCE)
        source_cursor = source_conn.cursor(dictionary=True)
        print(f"✓ Connected to source: {SOURCE['host']}")
    except Exception as e:
        print(f"✗ Failed to connect to source: {e}")
        return False
    
    # Connect to destination
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Connecting to destination database...")
    try:
        dest_conn = mysql.connector.connect(**DEST)
        dest_cursor = dest_conn.cursor()
        print(f"✓ Connected to destination: {DEST['host']}")
    except Exception as e:
        print(f"✗ Failed to connect to destination: {e}")
        source_conn.close()
        return False
    
    # Get list of tables
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Fetching table list...")
    source_cursor.execute("SHOW TABLES")
    tables = [row[list(row.keys())[0]] for row in source_cursor.fetchall()]
    print(f"Found {len(tables)} tables to copy")
    
    # Copy each table
    for idx, table in enumerate(tables, 1):
        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] [{idx}/{len(tables)}] Copying table: {table}")
        
        try:
            # Get CREATE TABLE statement
            source_cursor.execute(f"SHOW CREATE TABLE `{table}`")
            create_stmt = source_cursor.fetchone()['Create Table']
            
            # Drop and recreate table in destination
            dest_cursor.execute(f"DROP TABLE IF EXISTS `{table}`")
            dest_cursor.execute(create_stmt)
            print(f"  ✓ Created table structure")
            
            # Get row count
            source_cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
            total_rows = source_cursor.fetchone()['cnt']
            print(f"  → {total_rows:,} rows to copy")
            
            if total_rows == 0:
                print(f"  ✓ No data to copy")
                continue
            
            # Copy data in batches
            batch_size = 1000
            offset = 0
            copied = 0
            
            while offset < total_rows:
                source_cursor.execute(f"SELECT * FROM `{table}` LIMIT {batch_size} OFFSET {offset}")
                rows = source_cursor.fetchall()
                
                if not rows:
                    break
                
                # Get column names
                columns = list(rows[0].keys())
                placeholders = ', '.join(['%s'] * len(columns))
                insert_sql = f"INSERT INTO `{table}` ({', '.join([f'`{c}`' for c in columns])}) VALUES ({placeholders})"
                
                # Insert batch
                values = [[row[col] for col in columns] for row in rows]
                dest_cursor.executemany(insert_sql, values)
                dest_conn.commit()
                
                copied += len(rows)
                offset += batch_size
                
                if copied % 10000 == 0 or copied == total_rows:
                    print(f"  → {copied:,}/{total_rows:,} rows copied ({int(copied/total_rows*100)}%)")
            
            print(f"  ✓ Completed: {copied:,} rows")
            
        except Exception as e:
            print(f"  ✗ Error copying {table}: {e}")
            continue
    
    # Close connections
    source_cursor.close()
    source_conn.close()
    dest_cursor.close()
    dest_conn.close()
    
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] ✓ Database copy completed!")
    return True

if __name__ == "__main__":
    success = copy_database()
    sys.exit(0 if success else 1)
