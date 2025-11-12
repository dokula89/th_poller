import json
import re
import sys
from pathlib import Path

def extract_bedrooms(text):
    if not text:
        return None
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:bd|bed|bedroom|br)', text, re.I)
    if m:
        return m.group(1)
    if re.search(r'studio', text, re.I):
        return 'Studio'
    return None

def extract_bathrooms(text):
    if not text:
        return None
    m = re.search(r'(\d+(?:\.\d+)?)\s*(?:ba|bath|bathroom)', text, re.I)
    if m:
        return m.group(1)
    return None

def extract_price(text):
    if not text:
        return None
    m = re.search(r'(\$[\d,]+(?:\.\d{2})?)', text)
    if m:
        return m.group(1)
    return None

def extract_listing_id(listing_website):
    if not listing_website:
        return None
    m = re.search(r'/([a-f0-9\-]{16,})', listing_website)
    if m:
        return m.group(1)
    return None

def best_address(item):
    for key in ['full_address', 'street', 'address', 'location']:
        if key in item and item[key]:
            return item[key]
    # Try to find address in description
    if 'description' in item and item['description']:
        m = re.search(r'(\d+\s+[^,]+,?\s*[^,]+,?\s*[A-Z]{2}\s*\d{5})', item['description'])
        if m:
            return m.group(1)
    return None

def fix_listing(item):
    # Bedrooms
    for field in ['title', 'description']:
        val = extract_bedrooms(item.get(field, ''))
        if val:
            item['bedrooms'] = val
            break
    # Bathrooms
    for field in ['title', 'description']:
        val = extract_bathrooms(item.get(field, ''))
        if val:
            item['bathrooms'] = val
            break
    # Price
    for field in ['price', 'title', 'description']:
        val = extract_price(item.get(field, ''))
        if val:
            item['price'] = val
            break
    # Full address
    addr = best_address(item)
    if addr:
        item['full_address'] = addr
    # Listing ID
    item['listing_id'] = extract_listing_id(item.get('listing_website', ''))
    return item

def main():
    if len(sys.argv) < 2:
        print('Usage: python fix_extracted_listings.py path/to/extracted_listings.json')
        sys.exit(1)
    path = Path(sys.argv[1])
    with path.open('r', encoding='utf-8') as f:
        data = json.load(f)
    fixed = [fix_listing(dict(item)) for item in data]
    out_path = path.parent / (path.stem + '_fixed.json')
    with out_path.open('w', encoding='utf-8') as f:
        json.dump(fixed, f, ensure_ascii=False, indent=2)
    print(f'Wrote {len(fixed)} listings to {out_path}')

if __name__ == '__main__':
    main()
