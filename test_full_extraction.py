"""Test full extraction pipeline on popup"""
from PIL import Image, ImageEnhance
import pytesseract
import json
import re
from pathlib import Path

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load the popup
popup_path = Path('Captures/parcels/parcels_969.png')
img = Image.open(popup_path)
print(f"Original popup: {img.width}x{img.height}")

# Upscale 4x
upscaled = img.resize((img.width * 4, img.height * 4), Image.LANCZOS)
print(f"Upscaled to: {upscaled.width}x{upscaled.height}")

# Enhance contrast
enhancer = ImageEnhance.Contrast(upscaled)
enhanced = enhancer.enhance(2.0)

# OCR
text = pytesseract.image_to_string(enhanced, config=r'--oem 3 --psm 6')
print(f"\nOCR extracted {len(text)} characters")
print("="*60)
print(text)
print("="*60)

# Extract fields using the same patterns as parcel_automation.py
patterns = {
    'parcel_number': [
        r'Parcel[:\s#]*(\d+)',
        r'(\d{10})',
    ],
    'property_name': [
        r'[Pp]roperty\s*name[:\s]*([^\n]+)',
        r'name[:\s]*([A-Z][A-Za-z\s]+)',
    ],
    'jurisdiction': [
        r'[Jj]urisdic[t]?ion[:\s]*([^\n]+)',
        r'(SEATTLE|Seattle|Bellevue)',
    ],
    'taxpayer_name': [
        r'[Tt]axpayer\s*name[:\s]*([^\n]+)',
    ],
    'address': [
        r'[Aa]ddress[:\s]*([^\n]+)',
        r'[Aa]derass[:\s]*([^\n]+)',
    ],
    'appraised_value': [
        r'[Aa]ppraised\s*value[:\s]*\$?([\d,]+)',
    ],
    'lot_area': [
        r'[Ll]ot\s*area[:\s]*([\d,\.]+)',
        r'[Ll]oams[:\s]*([\d,\.]+)',
    ],
    'levy_code': [
        r'[Ll]evy\s*code[:\s]*(\d+)',
        r'[Ll]avycode[:\s]*(\d+)',
    ],
    'num_units': [
        r'#\s*of\s*units[:\s]*(\d+)',
        r'units[:\s]*(\d+)',
        r'atunk[^\d]*(\d+)',
    ],
    'num_buildings': [
        r'#\s*of\s*buildings[:\s]*(\d+)',
        r'buildings[:\s]*(\d+)',
        r'[Rr]oof\s*buildings[:\s]*(\d+)',
    ],
}

extracted_data = {}

print("\n\nEXTRACTED FIELDS:")
print("="*60)
for field_name, field_patterns in patterns.items():
    for pattern in field_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            extracted_data[field_name] = value
            print(f"{field_name}: {value}")
            break
    
    if field_name not in extracted_data:
        print(f"{field_name}: NOT FOUND")

# Save to JSON
output = {
    'id': 969,
    'raw_text': text,
    'extracted_fields': extracted_data
}

json_path = Path('Captures/parcels/test_extraction_969.json')
with open(json_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"\n✓ Saved to: {json_path}")
