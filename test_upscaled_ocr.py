"""Test OCR with upscaling"""
from PIL import Image, ImageEnhance
import pytesseract
from pathlib import Path

# Configure Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Load popup
popup_path = Path('Captures/parcels/parcels_969.png')
img = Image.open(popup_path)
print(f"Original size: {img.width}x{img.height}")

# Upscale 4x
scale = 4
new_width = img.width * scale
new_height = img.height * scale
upscaled = img.resize((new_width, new_height), Image.LANCZOS)
print(f"Upscaled to: {upscaled.width}x{upscaled.height}")

# Enhance contrast
enhancer = ImageEnhance.Contrast(upscaled)
enhanced = enhancer.enhance(2.0)

# Save for inspection
enhanced.save('test_upscaled_enhanced.png')
print("Saved: test_upscaled_enhanced.png")

# OCR
text = pytesseract.image_to_string(enhanced, config=r'--oem 3 --psm 6')
print(f"\nExtracted {len(text)} characters:")
print("="*60)
print(text)
print("="*60)

# Check for CHARBERIN
if 'CHARBERIN' in text.upper() or 'CHARL' in text.upper():
    print("\n✓ Found property name in text!")
else:
    print("\n✗ Property name not found")
