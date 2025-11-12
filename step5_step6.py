#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Step 5: Match addresses from JSON entries to DB records using files under th_poller/step5.
Step 6: Insert JSON into DB.
"""
import os
import json
import mysql.connector as mysql
from pathlib import Path
from config_utils import CFG

def get_addresses_from_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    return [e.get("address", "").strip() for e in entries if e.get("address")]

def match_addresses(addresses, conn):
    cur = conn.cursor(dictionary=True)
    matched = []
    for addr in addresses:
        cur.execute("SELECT * FROM apartment_listings WHERE address=%s", (addr,))
        result = cur.fetchone()
        if result:
            matched.append((addr, result))
    cur.close()
    return matched

def step5_match_addresses():
    # Use JSON files from previous step (e.g., extracted_listings.json in today's folder)
    from datetime import datetime
    base_dir = Path(__file__).parent / "Captures" / datetime.now().strftime("%Y-%m-%d")
    all_addresses = set()
    for file in base_dir.glob("extracted_listings*.json"):
        all_addresses.update(get_addresses_from_json(file))
    conn = mysql.connect(
        host=CFG["MYSQL_HOST"],
        port=CFG["MYSQL_PORT"],
        user=CFG["MYSQL_USER"],
        password=CFG["MYSQL_PASSWORD"],
        database=CFG["MYSQL_DB"]
    )
    matches = match_addresses(list(all_addresses), conn)
    print(f"Matched {len(matches)} addresses:")
    for addr, rec in matches:
        print(f"{addr} -> {rec}")
    conn.close()

def step6_insert_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        entries = json.load(f)
    conn = mysql.connect(
        host=CFG["MYSQL_HOST"],
        port=CFG["MYSQL_PORT"],
        user=CFG["MYSQL_USER"],
        password=CFG["MYSQL_PASSWORD"],
        database=CFG["MYSQL_DB"]
    )
    cur = conn.cursor()
    for entry in entries:
        address = entry.get("address", "").strip()
        price = entry.get("price")
        # Add more fields as needed
        cur.execute("INSERT INTO apartment_listings (address, price) VALUES (%s, %s)", (address, price))
    conn.commit()
    cur.close()
    conn.close()
    print(f"Inserted {len(entries)} entries into apartment_listings.")

if __name__ == "__main__":
    # Example usage:
    step5_match_addresses()
    # step6_insert_json('path_to_json.json')
