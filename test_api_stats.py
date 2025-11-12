import requests
import json
from urllib.parse import quote

address = "111 ALOHA ST, Seattle, WA 98109"
encoded_address = quote(address)
url = f"http://localhost/step5/find_or_create_place.php?address={encoded_address}&html=yes&debug=1"

print("Testing API endpoint...")
print(f"URL: {url}")
print("\n" + "="*60 + "\n")

try:
    response = requests.get(url, timeout=(8, 90))
    print(f"Status Code: {response.status_code}")
    print(f"\nResponse Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    
    print(f"\nResponse Body:")
    try:
        result = response.json()
        print(json.dumps(result, indent=2))
        
        # Highlight API stats
        if 'api_call_stats' in result:
            print("\n" + "="*60)
            print("API CALL STATS FOUND:")
            print("="*60)
            stats = result['api_call_stats']
            print(f"  Today:      {stats.get('today', 0)}")
            print(f"  Last Week:  {stats.get('last_week', 0)}")
            print(f"  Last Month: {stats.get('last_month', 0)}")
        else:
            print("\n" + "="*60)
            print("⚠ WARNING: api_call_stats NOT FOUND in response!")
            print("="*60)
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON: {e}")
        print(f"Raw response: {response.text[:500]}")
        
except Exception as e:
    print(f"Error: {e}")
