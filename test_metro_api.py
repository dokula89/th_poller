"""Test the metro API loader"""
import requests

api_url = "http://localhost/step5/get_major_metros.php?only=names"
print(f"Testing: {api_url}")

try:
    r = requests.get(api_url, timeout=8)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Response: {data}")
        
        names = []
        if isinstance(data, dict):
            if isinstance(data.get('names'), list):
                names = [str(x).strip() for x in data.get('names') if x]
            elif isinstance(data.get('rows'), list):
                for m in data['rows']:
                    if isinstance(m, dict):
                        nm = m.get('metro_name')
                        if nm:
                            names.append(str(nm).strip())
        
        names = sorted(list(dict.fromkeys([n for n in names if n])))
        print(f"\nParsed names: {names}")
        print(f"Count: {len(names)}")
        
        placeholder = "Select: major_metros"
        values = [placeholder, "All"] + names if names else [placeholder, "All"]
        print(f"\nFinal dropdown values: {values}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
