"""Test unit extraction and address cleaning for various formats"""
import re

test_addresses = [
    "617 - 3rd Ave W - 208, Seattle, WA",
    "1415 6th Ave N, Seattle, WA 98109",
    "2207 W. RAYE ST #503, Seattle, WA 98199",
    "1017 E HARRISON ST #A, Seattle, WA 98102",
    "123 Main St Apt 4B, Seattle, WA 98101",
    "500 Wall St Unit 2301, Seattle, WA 98121",
]

unit_patterns = [
    (r'#\s*([A-Za-z0-9\-]+)', "#503, #A"),
    (r'\b(?:apt|apartment|unit|suite|ste)\s*\.?\s*([A-Za-z0-9\-]+)', "Apt 4B, Unit 123"),
    (r'\s-\s(\d+[A-Za-z]?),\s', "- 208, (dash + unit before comma)"),
    (r'\s+([A-Za-z]?\d{2,4}[A-Za-z]?),\s', "space + unit before comma"),
]

strip_patterns = [
    r'\b(apt|apartment|unit|suite|ste|bldg|building|floor|fl)\s*\.?\s*[a-z0-9\-]+',
    r'\s*#\s*[a-z0-9\-]+',
    r'\s-\s\d+[a-z]?,',  # " - 208," (dash + unit before comma)
    r'\s+[a-z]\d+[a-z]?,\s',
    r'\s+\d+[a-z]\d*,\s',
]

print("=" * 80)
print("UNIT EXTRACTION AND ADDRESS CLEANING TEST")
print("=" * 80)

for addr in test_addresses:
    print(f"\nOriginal: {addr}")
    
    # Extract unit
    unit_name = None
    for pattern, desc in unit_patterns:
        match = re.search(pattern, addr, re.I)
        if match:
            unit_name = match.group(1).strip()
            print(f"  Unit: {unit_name} (matched: {desc})")
            break
    
    if not unit_name:
        print(f"  Unit: None")
    
    # Clean address
    cleaned = addr
    for pattern in strip_patterns:
        cleaned = re.sub(pattern, ',', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r',\s*,', ',', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip(', ')
    
    print(f"  Google: {cleaned}")
