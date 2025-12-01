#!/usr/bin/env python3
"""
Find the popup by looking for the small orange King County icon box
that appears at the top-left of the popup
"""
from PIL import Image
import numpy as np

# Load the screenshot
img = Image.open('Captures/parcels/debug_original_215247.png')
img_array = np.array(img)

# The popup has a small dark orange/brown icon box at top-left
# Looking for the King County icon which is darker: around RGB(180, 100, 0) to RGB(210, 130, 20)
# This is the small square icon at the top-left of the popup

# Create mask for the icon color (darker orange/brown)
lower_icon = np.array([160, 80, 0])
upper_icon = np.array([220, 140, 30])

mask = np.all((img_array >= lower_icon) & (img_array <= upper_icon), axis=2)

print(f"Found {np.sum(mask)} pixels matching icon color")

if np.sum(mask) > 50:  # Need at least 50 pixels for the icon
    # Find all coordinates where mask is True
    coords = np.argwhere(mask)
    
    if len(coords) > 0:
        # Get bounding box of icon pixels
        y_min, x_min = coords.min(axis=0)
        y_max, x_max = coords.max(axis=0)
        
        print(f"Icon found at: x={x_min}-{x_max}, y={y_min}-{y_max}")
        print(f"Icon size: {x_max - x_min}px x {y_max - y_min}px")
        
        # The popup extends to the right and down from the icon
        # Based on your screenshots, popup is roughly 220px wide x 170px tall
        popup_width = 220
        popup_height = 170
        
        # Top-left of popup is near the icon
        popup_x = x_min - 5  # Small padding
        popup_y = y_min - 5
        popup_right = popup_x + popup_width
        popup_bottom = popup_y + popup_height
        
        # Make sure we don't go out of bounds
        popup_x = max(0, popup_x)
        popup_y = max(0, popup_y)
        popup_right = min(img.width, popup_right)
        popup_bottom = min(img.height, popup_bottom)
        
        print(f"Popup bounds: ({popup_x}, {popup_y}) to ({popup_right}, {popup_bottom})")
        print(f"Popup size: {popup_right - popup_x}px x {popup_bottom - popup_y}px")
        
        # Crop the popup
        popup = img.crop((popup_x, popup_y, popup_right, popup_bottom))
        popup.save('Captures/parcels/test_icon_based_crop.png')
        print("Saved to test_icon_based_crop.png")
        
        # Also show the icon itself
        icon_crop = img.crop((x_min, y_min, x_max + 1, y_max + 1))
        icon_crop.save('Captures/parcels/test_icon_only.png')
        print("Saved icon to test_icon_only.png")
else:
    print("Icon not found - trying to visualize what colors are present")
    # Sample a small area where popup should be (center-left area)
    sample_region = img_array[250:450, 600:900]
    unique_colors = {}
    for y in range(sample_region.shape[0]):
        for x in range(sample_region.shape[1]):
            color = tuple(sample_region[y, x])
            unique_colors[color] = unique_colors.get(color, 0) + 1
    
    # Show top 10 most common colors
    sorted_colors = sorted(unique_colors.items(), key=lambda x: x[1], reverse=True)
    print("\nTop 10 colors in popup area:")
    for color, count in sorted_colors[:10]:
        print(f"  RGB{color}: {count} pixels")
