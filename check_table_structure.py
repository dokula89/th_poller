"""
Check king_county_parcels table structure
"""
import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '',
    'database': 'offta'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    cursor.execute("DESCRIBE king_county_parcels")
    columns = cursor.fetchall()
    
    print("\n=== king_county_parcels table structure ===\n")
    print(f"{'Field':<30} {'Type':<20} {'Null':<5} {'Key':<5} {'Default':<10}")
    print("-" * 80)
    for col in columns:
        print(f"{col[0]:<30} {col[1]:<20} {col[2]:<5} {col[3]:<5} {str(col[4]):<10}")
    
    print("\n" + "=" * 80)
    print(f"\nTotal columns: {len(columns)}")
    
    # Check if specific columns exist
    column_names = [col[0] for col in columns]
    required_cols = ['num_units', 'num_buildings', 'parcel_number', 'property_name']
    
    print("\nRequired columns check:")
    for req_col in required_cols:
        exists = "✓" if req_col in column_names else "✗ MISSING"
        print(f"  {req_col}: {exists}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"\n✗ Error: {e}")
    import traceback
    traceback.print_exc()
