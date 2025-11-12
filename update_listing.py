#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script to update a row in apartment_listings when edited.
Usage: python update_listing.py <listing_id> <field> <new_value>
"""
import sys
import mysql.connector as mysql
from config_utils import CFG

def update_listing(listing_id, field, new_value):
    try:
        conn = mysql.connect(
            host=CFG["MYSQL_HOST"],
            port=CFG["MYSQL_PORT"],
            user=CFG["MYSQL_USER"],
            password=CFG["MYSQL_PASSWORD"],
            database=CFG["MYSQL_DB"]
        )
        cur = conn.cursor()
        sql = f"UPDATE apartment_listings SET {field}=%s WHERE listing_id=%s"
        cur.execute(sql, (new_value, listing_id))
        conn.commit()
        print(f"Updated {field} for listing_id={listing_id} to {new_value}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error updating listing: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python update_listing.py <listing_id> <field> <new_value>")
        sys.exit(1)
    update_listing(sys.argv[1], sys.argv[2], sys.argv[3])
