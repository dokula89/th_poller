#!/usr/bin/env python
"""Test auto capture logic"""
import mysql.connector
from config_hud_db import DB_CONFIG
from pathlib import Path

conn = mysql.connector.connect(**DB_CONFIG)
cursor = conn.cursor(dictionary=True)

# Get ALL candidates (no limit)
cursor.execute("""
    SELECT ga.id
    FROM google_addresses ga
    INNER JOIN major_metros mm ON mm.id = ga.metro_id
    WHERE ga.king_county_parcels_id IS NULL
    AND ga.json_dump IS NOT NULL
    AND JSON_EXTRACT(ga.json_dump, '$.result') IS NOT NULL
    AND mm.metro_name = %s
    ORDER BY ga.id ASC
""", ('Seattle',))

candidates = cursor.fetchall()
print(f'Total candidates without parcel: {len(candidates)}')

# Check which ones have images
parcels_dir = Path(r"C:\Users\dokul\Desktop\robot\th_poller\Captures\parcels")
no_image = []
has_image = []

for candidate in candidates:
    addr_id = candidate['id']
    image_file = parcels_dir / f"parcels_{addr_id}.png"
    processed_file = parcels_dir / f"parcels_{addr_id}_processed.png"
    skipped_file = parcels_dir / f"parcels_{addr_id}_skipped.png"
    
    if not image_file.exists() and not processed_file.exists() and not skipped_file.exists():
        no_image.append(addr_id)
    else:
        has_image.append(addr_id)

print(f"Without any image file: {len(no_image)}")
print(f"With image file: {len(has_image)}")

if no_image[:10]:
    print(f"First 10 without images: {no_image[:10]}")

cursor.close()
conn.close()
