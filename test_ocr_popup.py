"""Test OCR on the popup image"""
from PIL import Image
import pytesseract
from pathlib import Path
import re

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Test on the latest popup
captures_dir = Path('Captures/parcels')
popups = sorted(captures_dir.glob('parcels_*.png'))

if not popups:
    print("No popup images found!")
    exit(1)

latest_popup = popups[-1]
print(f"Testing OCR on: {latest_popup.name}")

# Load image
img = Image.open(latest_popup)
print(f"Image size: {img.width}x{img.height}")

# Try different OCR configurations
configs = [
    ('PSM 3 - Fully automatic', r'--oem 3 --psm 3'),
    ('PSM 6 - Uniform block', r'--oem 3 --psm 6'),
    ('PSM 11 - Sparse text', r'--oem 3 --psm 11'),
    ('PSM 4 - Single column', r'--oem 3 --psm 4'),
]

best_text = ""
best_config = ""

for name, config in configs:
    try:
        text = pytesseract.image_to_string(img, config=config)
        print(f"\n{'='*60}")
        print(f"{name}: {len(text)} chars")
        print(f"{'='*60}")
        print(text)
        
        if len(text) > len(best_text):
            best_text = text
            best_config = name
    except Exception as e:
        print(f"{name} failed: {e}")

print(f"\n{'='*60}")
print(f"BEST: {best_config} with {len(best_text)} chars")
print(f"{'='*60}")

# Try to extract property name
property_patterns = [
    r'Property\s*name[:\s]*([^\n]+)',
    r'Property[:\s]*([^\n]+)',
    r'name[:\s]*([A-Z][^\n]+)',
]

print("\nTrying to extract Property Name:")
for pattern in property_patterns:
    match = re.search(pattern, best_text, re.IGNORECASE)
    if match:
        print(f"  Pattern '{pattern}' found: {match.group(1)}")
    else:
        print(f"  Pattern '{pattern}' - NO MATCH")

# Check if "CHARBERIN" or similar appears anywhere
if 'CHARBERIN' in best_text.upper():
    print("\n✓ Found 'CHARBERIN' in text")
else:
    print("\n✗ 'CHARBERIN' not found in OCR output")
