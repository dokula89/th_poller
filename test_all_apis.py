"""Test all the APIs used by the app"""
import requests

def test_api(name, url):
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url}")
    try:
        r = requests.get(url, timeout=10)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, dict):
                print(f"OK: {data.get('ok', False)}")
                if data.get('ok'):
                    if 'rows' in data:
                        print(f"Rows: {len(data.get('rows', []))}")
                    if 'accounts' in data:
                        print(f"Accounts: {len(data.get('accounts', []))}")
                    if 'names' in data:
                        print(f"Names: {data.get('names', [])}")
                    print(f"✓ {name} working")
                else:
                    print(f"✗ Error: {data.get('error')}")
            else:
                print(f"✗ Unexpected response type: {type(data)}")
        else:
            print(f"✗ HTTP Error: {r.status_code}")
    except Exception as e:
        print(f"✗ Exception: {e}")

# Test all APIs
test_api("Metro Names", "http://localhost/step5/get_major_metros.php?only=names")
test_api("Parcel Metros", "http://localhost/step5/get_parcel_metros.php")
test_api("Accounts", "http://localhost/step5/get_accounts.php?limit=5")
test_api("Websites", "http://localhost/step5/get_websites.php?limit=5")

print(f"\n{'='*60}")
print("All API tests completed!")
