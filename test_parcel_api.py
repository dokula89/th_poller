"""Test the Parcel API endpoint"""
import requests

# Test 1: All metros
print("Test 1: Get all parcel metros")
url = "http://localhost/step5/get_parcel_metros.php"
r = requests.get(url, timeout=10)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Response: {data}")
    if data.get('ok'):
        print(f"✓ Success: {data.get('total')} metros returned")
        for row in data.get('rows', []):
            print(f"  - {row.get('metro_name')}: {row.get('county_name')} ({row.get('parcel_link')})")
    else:
        print(f"✗ Error: {data.get('error')}")
else:
    print(f"✗ HTTP Error: {r.status_code}")

print("\n" + "="*60 + "\n")

# Test 2: Filter by Seattle
print("Test 2: Get Seattle metros only")
url = "http://localhost/step5/get_parcel_metros.php?metro=Seattle"
r = requests.get(url, timeout=10)
print(f"Status: {r.status_code}")
if r.status_code == 200:
    data = r.json()
    print(f"Response: {data}")
    if data.get('ok'):
        print(f"✓ Success: {data.get('total')} metros returned")
        for row in data.get('rows', []):
            print(f"  - {row.get('metro_name')}: {row.get('county_name')} ({row.get('parcel_link')})")
    else:
        print(f"✗ Error: {data.get('error')}")
else:
    print(f"✗ HTTP Error: {r.status_code}")
