#!/usr/bin/env python3
"""
Test the updated popup detection with RGB(255, 185, 91)
"""
from PIL import Image
import numpy as np

img = Image.open('Captures/parcels/debug_original_215247.png')
img_array = np.array(img)

print(f"Image size: {img.size}")
print("Detecting popup by background color RGB(255, 185, 91)...")

lower_popup = np.array([250, 180, 88])  # Match parcel_automation.py
upper_popup = np.array([255, 190, 94])

popup_mask = np.all((img_array >= lower_popup) & (img_array <= upper_popup), axis=2)
popup_pixels = np.sum(popup_mask)

print(f"Found {popup_pixels} pixels matching popup color")

if popup_pixels >= 100:
    # Get bounding box
    popup_coords = np.argwhere(popup_mask)
    min_y = popup_coords[:, 0].min()
    max_y = popup_coords[:, 0].max()
    min_x = popup_coords[:, 1].min()
    max_x = popup_coords[:, 1].max()
    
    print(f"Popup bounds: x={min_x}-{max_x}, y={min_y}-{max_y}")
    print(f"Popup size: {max_x - min_x}px x {max_y - min_y}px")
    
    # Add padding
    padding = 15
    popup_left = max(0, min_x - padding)
    popup_top = max(0, min_y - padding)
    popup_right = min(img.width, max_x + padding)
    popup_bottom = min(img.height, max_y + padding)
    
    print(f"With padding: ({popup_left}, {popup_top}) to ({popup_right}, {popup_bottom})")
    print(f"Final size: {popup_right - popup_left}px x {popup_bottom - popup_top}px")
    
    # Crop and save
    popup = img.crop((popup_left, popup_top, popup_right, popup_bottom))
    popup.save('Captures/parcels/test_color_based_crop.png')
    print("✓ Saved to test_color_based_crop.png")
else:
    print("✗ Not enough pixels found")
