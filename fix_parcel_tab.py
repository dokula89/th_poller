"""
Fix Parcel tab to show google_addresses WITHOUT king_county_parcels_id (not those WITH it)
Also add statistics showing how many addresses have/don't have parcel data
"""

# Read the file
with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the parcel query section (around line 4800-4850)
old_query = """                    query = f\"\"\"
                        SELECT 
                            kcp.id,
                            kcp.Address as address,
                            kcp.Property_name,
                            kcp.num_of_units,
                            kcp.Appraised_value,
                            mm.metro_name,
                            mm.parcel_link,
                            CONCAT(
                                '{{',
                                '"Property_name":"', IFNULL(kcp.Property_name, ''), '",',
                                '"Present_use":"', IFNULL(kcp.Present_use, ''), '",',
                                '"Jurisdiction":"', IFNULL(kcp.Jurisdiction, ''), '",',
                                '"Taxpayer_name":"', IFNULL(kcp.Taxpayer_name, ''), '",',
                                '"Appraised_value":"', IFNULL(kcp.Appraised_value, ''), '",',
                                '"Lot_area":"', IFNULL(kcp.Lot_area, ''), '",',
                                '"num_of_units":"', IFNULL(kcp.num_of_units, ''), '",',
                                '"num_of_buildings":"', IFNULL(kcp.num_of_buildings, ''), '",',
                                '"Levy_code":"', IFNULL(kcp.Levy_code, ''), '"',
                                '}}'
                            ) as json_dump
                        FROM king_county_parcels kcp
                        INNER JOIN google_addresses ga ON ga.king_county_parcels_id = kcp.id
                        INNER JOIN major_metros mm ON mm.id = ga.metro_id
                        {where_clause}
                        ORDER BY kcp.id DESC 
                        LIMIT 500
                    \"\"\"
                    
                    cursor.execute(query, params)
                    parcels = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    
                    rows = []
                    parcel_link_found = None
                    for parcel in parcels:
                        plink = parcel.get('parcel_link') or ''
                        if plink and not parcel_link_found:
                            parcel_link_found = plink
                            log_to_file(f"[Parcel] Found parcel_link: {plink}")
                        rows.append({
                            'id': parcel.get('id'),
                            'address': parcel.get('address') or '',
                            'metro_name': parcel.get('metro_name') or '',
                            'parcel_link': plink,
                            'json_dump': parcel.get('json_dump') or '{}',
                            'run_interval_minutes': 0,
                            'next_run': None,
                            'processed_at': None,
                            'status': 'ready',
                            'steps': {}
                        })"""

new_query = """                    # First, get statistics for the status label
                    stats_query = \"\"\"
                        SELECT 
                            COUNT(*) as total_addresses,
                            SUM(CASE WHEN king_county_parcels_id IS NOT NULL THEN 1 ELSE 0 END) as with_parcel,
                            SUM(CASE WHEN king_county_parcels_id IS NULL THEN 1 ELSE 0 END) as without_parcel
                        FROM google_addresses ga
                        INNER JOIN major_metros mm ON mm.id = ga.metro_id
                        WHERE mm.metro_name = %s
                    \"\"\"
                    cursor.execute(stats_query, [metro_filter])
                    stats = cursor.fetchone()
                    total_addresses = stats.get('total_addresses', 0) or 0
                    with_parcel = stats.get('with_parcel', 0) or 0
                    without_parcel = stats.get('without_parcel', 0) or 0
                    log_to_file(f"[Parcel] Stats for {metro_filter}: {without_parcel} without parcel, {with_parcel} with parcel, {total_addresses} total")
                    
                    # Update status label with stats (on main thread)
                    stats_text = f"📊 {without_parcel} addresses without parcel data | {with_parcel} with parcel data | {total_addresses} total"
                    if hasattr(self, '_queue_status_label'):
                        self._root.after(0, lambda: self._queue_status_label.config(text=stats_text))
                    
                    # Query google_addresses WITHOUT king_county_parcels_id (addresses that need processing)
                    query = f\"\"\"
                        SELECT 
                            ga.id,
                            ga.full_address as address,
                            mm.metro_name,
                            mm.parcel_link
                        FROM google_addresses ga
                        INNER JOIN major_metros mm ON mm.id = ga.metro_id
                        WHERE ga.king_county_parcels_id IS NULL
                        AND ga.full_address IS NOT NULL 
                        AND ga.full_address != ''
                        AND mm.metro_name = %s
                        ORDER BY ga.id DESC 
                        LIMIT 500
                    \"\"\"
                    
                    cursor.execute(query, [metro_filter])
                    parcels = cursor.fetchall()
                    cursor.close()
                    conn.close()
                    
                    rows = []
                    parcel_link_found = None
                    for parcel in parcels:
                        plink = parcel.get('parcel_link') or ''
                        if plink and not parcel_link_found:
                            parcel_link_found = plink
                            log_to_file(f"[Parcel] Found parcel_link: {plink}")
                        rows.append({
                            'id': parcel.get('id'),
                            'address': parcel.get('address') or '',
                            'metro_name': parcel.get('metro_name') or '',
                            'parcel_link': plink,
                            'json_dump': '{}',  # No data yet (address needs processing)
                            'run_interval_minutes': 0,
                            'next_run': None,
                            'processed_at': None,
                            'status': 'ready',
                            'steps': {}
                        })"""

if old_query in content:
    content = content.replace(old_query, new_query)
    print("✓ Updated Parcel tab query to show addresses WITHOUT king_county_parcels_id")
    print("✓ Added statistics showing how many addresses have/don't have parcel data")
    
    with open('config_hud.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Saved config_hud.py")
else:
    print("❌ Could not find the query section to replace")
    print("The code structure may have changed. Please manually update the query.")
