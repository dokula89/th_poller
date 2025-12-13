import mysql.connector

conn = mysql.connector.connect(
    host='172.104.206.182',
    port=3306,
    user='seattlelisted_usr',
    password='T@5z6^pl}',
    database='offta'
)
cursor = conn.cursor()

# Count with King County filter
cursor.execute("SELECT COUNT(*) FROM google_addresses WHERE king_county_parcels_id IS NULL AND (parcel_error IS NULL OR parcel_error = '') AND json_dump LIKE '%King County%'")
king_county_count = cursor.fetchone()[0]
print(f"King County addresses (no parcel, no error): {king_county_count}")

# Count all without parcel
cursor.execute("SELECT COUNT(*) FROM google_addresses WHERE king_county_parcels_id IS NULL AND (parcel_error IS NULL OR parcel_error = '')")
all_count = cursor.fetchone()[0]
print(f"All addresses (no parcel, no error): {all_count}")

# Check ID 922 specifically
cursor.execute("SELECT json_dump LIKE '%King County%' as has_king FROM google_addresses WHERE id = 922")
result = cursor.fetchone()
print(f"\nID 922 has 'King County' in json_dump: {result[0]}")

cursor.close()
conn.close()
