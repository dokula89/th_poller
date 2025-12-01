#!/usr/bin/env python3
"""
Simple approach: The popup has WHITE text labels like "Property name:", "Jurisdiction:", etc.
The rest of the page doesn't have white text in that area.
Just find the bounding box of white text pixels.
"""
from PIL import Image
import numpy as np

# Load the screenshot  
img = Image.open('Captures/parcels/debug_original_215247.png')
img_array = np.array(img)

# Look for white/light colored text (RGB > 200, 200, 200)
# This should only appear in the popup info box
mask = np.all(img_array > [200, 200, 200], axis=2)

print(f"Found {np.sum(mask)} white pixels")

if np.sum(mask) > 100:  # Need enough pixels for text
    # Find all white pixel coordinates
    coords = np.argwhere(mask)
    
    if len(coords) > 0:
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        print(f"White text bounding box: x={x_min}-{x_max}, y={y_min}-{y_max}")
        
        # Add padding around the text to get the full popup
        padding = 15
        popup_x = max(0, x_min - padding)
        popup_y = max(0, y_min - padding)
        popup_right = min(img.width, x_max + padding)
        popup_bottom = min(img.height, y_max + padding)
        
        print(f"Popup with padding: ({popup_x}, {popup_y}) to ({popup_right}, {popup_bottom})")
        print(f"Popup size: {popup_right - popup_x}px x {popup_bottom - popup_y}px")
        
        # Crop and save
        popup = img.crop((popup_x, popup_y, popup_right, popup_bottom))
        popup.save('Captures/parcels/test_white_text_crop.png')
        print("Saved to test_white_text_crop.png")
else:
    print("Not enough white pixels found")
