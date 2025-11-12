import requests

def check(url):
    print('URL:', url)
    try:
        r = requests.get(url, timeout=10)
        print('Status:', r.status_code)
        if r.status_code == 200:
            d = r.json()
            print('ok:', d.get('ok'), 'rows:', len(d.get('rows', [])))
        else:
            print('HTTP error')
    except Exception as e:
        print('Error:', e)

if __name__ == '__main__':
    check('http://localhost/step5/get_code_cities.php?limit=50')
    check('http://localhost/step5/get_911_cities.php?limit=50')
