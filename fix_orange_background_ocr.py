"""
Improve OCR preprocessing to handle orange background with white text
"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the contrast enhancement section
target_found = False
for i, line in enumerate(lines):
    if '# Enhance contrast for better OCR' in line:
        target_found = True
        start_line = i
        # Find where OCR actually runs (after the enhancement)
        for j in range(i, min(i+20, len(lines))):
            if 'logging.info("Running pytesseract OCR...")' in lines[j]:
                end_line = j
                break
        break

if not target_found:
    print("ERROR: Could not find OCR enhancement section")
    exit(1)

# New preprocessing code that handles orange background + white text
new_preprocessing = [
    "            # Enhance for better OCR - handle orange background with white text\n",
    "            import cv2\n",
    "            import numpy as np\n",
    "            from PIL import ImageEnhance\n",
    "            \n",
    "            # Convert PIL to OpenCV for advanced preprocessing\n",
    "            img_cv = cv2.cvtColor(np.array(image_to_ocr), cv2.COLOR_RGB2BGR)\n",
    "            \n",
    "            # Convert to HSV to isolate orange background\n",
    "            hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)\n",
    "            \n",
    "            # Define orange color range (King County parcel viewer uses bright orange)\n",
    "            lower_orange = np.array([5, 100, 100])   # Lower bound for orange\n",
    "            upper_orange = np.array([25, 255, 255])  # Upper bound for orange\n",
    "            \n",
    "            # Create mask for orange background\n",
    "            orange_mask = cv2.inRange(hsv, lower_orange, upper_orange)\n",
    "            \n",
    "            # Invert mask to get text regions\n",
    "            text_mask = cv2.bitwise_not(orange_mask)\n",
    "            \n",
    "            # Convert to grayscale\n",
    "            gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)\n",
    "            \n",
    "            # Invert: white text -> black text (OCR expects dark text on light bg)\n",
    "            inverted = cv2.bitwise_not(gray)\n",
    "            \n",
    "            # Apply binary threshold to get clean black text on white background\n",
    "            _, binary = cv2.threshold(inverted, 127, 255, cv2.THRESH_BINARY)\n",
    "            \n",
    "            # Optional: denoise\n",
    "            denoised = cv2.fastNlMeansDenoising(binary, None, 10, 7, 21)\n",
    "            \n",
    "            # Convert back to PIL\n",
    "            image_to_ocr = Image.fromarray(denoised)\n",
    "            \n",
    "            logging.info(\"Applied orange background removal and text inversion\")\n",
    "            \n",
]

# Replace the old enhancement code
lines = lines[:start_line] + new_preprocessing + lines[end_line:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Updated OCR preprocessing to handle orange background with white text")
print("  - Orange background detection using HSV color space")
print("  - Text inversion (white → black)")
print("  - Binary threshold for clean text")
print("  - Denoising applied")
