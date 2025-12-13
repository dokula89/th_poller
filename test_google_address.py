import re

def process_address(full_address):
    result = {'full_address': full_address, 'unit_name': None, 'google_address': None}
    
    if full_address:
        # Extract unit
        unit_patterns = [
            r'#\s*([A-Za-z0-9\-]+)',
            r'\b(?:apt|apartment|unit|suite|ste)\s*\.?\s*([A-Za-z0-9\-]+)',
            r'\s+([A-Za-z]?\d{2,4}[A-Za-z]?),\s',
        ]
        for pattern in unit_patterns:
            unit_match = re.search(pattern, full_address, re.I)
            if unit_match:
                result['unit_name'] = unit_match.group(1).strip()
                break
        
        # Generate google_address
        strip_patterns = [
            r'\b(apt|apartment|unit|suite|ste|bldg|building|floor|fl)\s*\.?\s*[a-z0-9\-]+',
            r'\s*#\s*[a-z0-9\-]+',
            r'\s+[a-z]\d+[a-z]?,\s',
            r'\s+\d+[a-z]\d*,\s',
        ]
        cleaned = full_address
        for pattern in strip_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r',\s*,', ',', cleaned)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        result['google_address'] = cleaned.strip(', ')
    
    return result

# Test
tests = [
    '2207 W. RAYE ST #503, Seattle, WA 98199',
    '1017 E HARRISON ST #A, Seattle, WA 98102',
    '123 Main St Apt 4B, Seattle, WA 98101',
]

for addr in tests:
    r = process_address(addr)
    print(f"full_address: {r['full_address']}")
    print(f"unit_name: {r['unit_name']}")
    print(f"google_address: {r['google_address']}")
    print()
