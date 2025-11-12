#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run SQL script to add newsletter columns and create log tables
"""

import mysql.connector

def run_sql_script():
    """Execute the SQL script"""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            port=3306,
            user='root',
            password='',
            database='offta',
            connect_timeout=10
        )
        cursor = conn.cursor()
        
        print("Reading SQL script...")
        with open('add_newsletter_columns.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()
        
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in sql_script.split(';') if s.strip()]
        
        print(f"Executing {len(statements)} SQL statements...\n")
        
        for i, statement in enumerate(statements, 1):
            try:
                print(f"[{i}/{len(statements)}] Executing...")
                # Print first 80 chars of statement
                preview = statement[:80].replace('\n', ' ')
                print(f"    {preview}...")
                
                cursor.execute(statement)
                conn.commit()
                print(f"    ✓ Success\n")
                
            except mysql.connector.Error as e:
                if "Duplicate column name" in str(e):
                    print(f"    ⚠️  Column already exists (skipping)\n")
                elif "Table" in str(e) and "already exists" in str(e):
                    print(f"    ⚠️  Table already exists (skipping)\n")
                else:
                    print(f"    ✗ Error: {e}\n")
        
        print("=" * 60)
        print("✓ Script execution completed")
        
        # Show current table structure
        print("\nNewsletter table structure:")
        cursor.execute("SHOW COLUMNS FROM newsletter")
        for col in cursor.fetchall():
            print(f"  - {col[0]} ({col[1]})")
        
        print("\nEmail send log table created:")
        cursor.execute("SHOW COLUMNS FROM email_send_log")
        for col in cursor.fetchall():
            print(f"  - {col[0]} ({col[1]})")
        
        print("\nSMS send log table created:")
        cursor.execute("SHOW COLUMNS FROM sms_send_log")
        for col in cursor.fetchall():
            print(f"  - {col[0]} ({col[1]})")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_sql_script()
