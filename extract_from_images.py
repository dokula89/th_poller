"""
Extract parcel data from images using OCR and update extraction patterns
Based on the two example images provided by user
"""

import cv2
import numpy as np
from PIL import Image
import pytesseract
import json
import re
from pathlib import Path

# Set Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def extract_parcel_from_image(image_path):
    """Extract parcel data from a single image"""
    print(f"\n{'='*60}")
    print(f"Processing: {image_path}")
    print(f"{'='*60}")
    
    # Read and preprocess image
    img = cv2.imread(str(image_path))
    if img is None:
        print(f"ERROR: Could not read image {image_path}")
        return None
    
    # Upscale 6x for better OCR
    height, width = img.shape[:2]
    img = cv2.resize(img, (width * 6, height * 6), interpolation=cv2.INTER_CUBIC)
    
    # Handle orange background with white text
    # Convert to HSV to isolate orange
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Orange color range (King County parcel viewer)
    lower_orange = np.array([5, 100, 100])
    upper_orange = np.array([25, 255, 255])
    
    # Create mask for orange background
    orange_mask = cv2.inRange(hsv, lower_orange, upper_orange)
    text_mask = cv2.bitwise_not(orange_mask)
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Invert: white text -> black text (OCR expects dark text on light bg)
    inverted = cv2.bitwise_not(gray)
    
    # Binary threshold for clean text
    _, binary = cv2.threshold(inverted, 127, 255, cv2.THRESH_BINARY)
    
    # Denoise
    denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)
    
    # Convert to PIL for OCR
    pil_img = Image.fromarray(denoised)
    
    # Extract text with OCR
    ocr_text = pytesseract.image_to_string(pil_img, config='--psm 6')
    
    print("\n--- RAW OCR TEXT ---")
    print(ocr_text[:1000])
    print("--- END RAW TEXT ---\n")
    
    # Extract structured data using patterns
    patterns = {
        'parcel_number': [
            r'[Pp]arc[ae]l[:\s]+([0-9A-Z]+)',  # Parcel or Parcal with space
            r'([0-9A-Z]{9,10})',
        ],
        'present_use': [
            r'[Pp]reseamtuse[:\s]*([^\n]+)',  # OCR: Preseamtuse
            r'[Pp]resent\s*use[:\s]*([^\n]+)',
            r'[Pp]rasent\s*use[:\s]*([^\n]+)',
        ],
        'property_name': [
            r'[Pp]roperty\s*name[:\s]*([^\n]+(?:\n[A-Z][^\n]+)?)',  # Multi-line support
            r'[Pp]ropary\s*name[:\s]*([^\n]+)',
        ],
        'jurisdiction': [
            r'[Aa]raacdion[:\s.]*([^\n]+)',  # OCR: Araacdion
            r'[Jj]uradiction[:\s]*([^\n]+)',  # OCR: Juradiktion
            r'[Jj]uracicion[:\s]*([^\n]+)',
            r'[Jj]urisdic[t]?ion[:\s]*([^\n]+)',
            r'(SEATTLE|BELLEVUE|RENTON|KENT|AUBURN|FEDERAL\s*WAY)',
        ],
        'taxpayer_name': [
            r'[Tt]axpayer\s+name[:\s]+(.+)',  # Standard
            r'[Tt]ax[xy]payer\s*name[:\s]*([^\n]+)',  # OCR: Taxypayer
            r'[Tt]aspeyer\s*name[:\s]*([^\n]+)',
        ],
        'address': [
            r'[Aa]ddress[:\s]*([^\n]+)',
            r'[Aa]gora[:\s]*([^\n]+)',
            r'([\$]?\d+[A-Z]?\s+[A-Z0-9\s]+(?:ST|AVE|RD|WAY|DR|BLVD|PL|LN|CT)[^\n]*)',
        ],
        'appraised_value': [
            r'Appraised\s*value[:\s]*\$?([\d,]+)',
            r'Appraised\s*valve[:\s]*\$?([\d,]+)',
        ],
        'lot_area': [
            r'[Ll]otarea[:\s]*([\d,\.]+)',  # OCR: Lotarea (no space)
            r'[Ll]et\s*area[:\s]*([\d,\.]+)',  # OCR: Let area
            r'[Ll]ot\s*aren[:\s]*([\d,\.]+)',
            r'[Ll]ot\s*area[:\s]*([\d,\.]+)',
        ],
        'num_units': [
            r'#ot\s*unts[:\s]+([\d]+)',  # OCR: #otunts
            r'[Zz]at\s*unts[:\s]+([\d]+)',  # OCR: Zatunts
            r'[Ff]ot\s*unts[:\s]+([\d]+)',  # OCR: Fotunts
            r'#\s*of\s*units[:\s]+([\d]+)',
            r'(\d+)\s*\n+\s*#\s*of\s*units:',
            r'#\s*at\s*unks[:\s]+([\d]+)',
        ],
        'num_buildings': [
            r'[Kk]oto[il]lings[:\s]+([\d]+)',  # OCR: kotoilings
            r'[Ss]of\s*buikiings[:\s]+([\d]+)',  # OCR: Sofbuikiings
            r'#\s*of\s*buildings[:\s]+([\d]+)',
            r'#\s*at\s*buildings[:\s]+([\d]+)',
        ],
        'levy_code': [
            r'[Ll]avy\s*code[:\s]+([O0-9]{3,4})',  # OCR: O13 (letter O instead of 0)
            r'[Ll]evy\s*code[:\s]+([O0-9]{3,4})',
            r'([O0-9]{4})\s*\n+\s*[Ll]avy\s*code:',
            r'[Ll]avy\s*cade[:\s]+([O0-9]+)',
        ],
    }
    
    extracted_data = {}
    
    for field, field_patterns in patterns.items():
        value = None
        for pattern in field_patterns:
            match = re.search(pattern, ocr_text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                print(f"✓ {field}: '{value}' (pattern: {pattern[:50]}...)")
                break
        
        if not value:
            print(f"✗ {field}: MISSING")
            value = "MISSING"
        
        extracted_data[field] = value
    
    return extracted_data

def main():
    """Process all parcel images and extract data"""
    
    parcels_dir = Path("Captures/parcels")
    
    # Find all PNG images
    image_files = list(parcels_dir.glob("*.png"))
    
    if not image_files:
        print("No PNG images found in Captures/parcels/")
        return
    
    print(f"Found {len(image_files)} images to process")
    
    all_extracted = []
    
    for image_path in image_files:
        data = extract_parcel_from_image(image_path)
        if data:
            data['source_image'] = image_path.name
            all_extracted.append(data)
    
    # Save extracted data
    output_file = parcels_dir / "extracted_from_images.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(all_extracted, f, indent=2)
    
    print(f"\n{'='*60}")
    print(f"✓ Extracted data from {len(all_extracted)} images")
    print(f"✓ Saved to: {output_file}")
    print(f"{'='*60}")
    
    # Show summary
    print("\n--- EXTRACTION SUMMARY ---")
    for i, data in enumerate(all_extracted, 1):
        print(f"\nImage {i}: {data['source_image']}")
        print(f"  Parcel: {data.get('parcel_number', 'N/A')}")
        print(f"  Property: {data.get('property_name', 'N/A')}")
        print(f"  Address: {data.get('address', 'N/A')}")
        print(f"  Jurisdiction: {data.get('jurisdiction', 'N/A')}")
        print(f"  Levy Code: {data.get('levy_code', 'N/A')}")
        print(f"  # Units: {data.get('num_units', 'N/A')}")

if __name__ == "__main__":
    main()
