import requests

r = requests.get('http://localhost/step5/get_empty_parcels_list.php?metro=Seattle&limit=10')
print(f"Status: {r.status_code}")
print(f"Response: {r.text[:1000]}")
