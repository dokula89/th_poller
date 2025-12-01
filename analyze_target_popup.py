"""Analyze the target popup dimensions from the attachment"""
from PIL import Image
import numpy as np

# The user's attachment shows the ideal popup extraction
# From the attachment, I can see it's approximately 220x140 pixels
# The popup has:
# - Darker orange header/icon on LEFT (~40 pixels wide)
# - Lighter beige/cream text area on RIGHT (rest of width)

# Let's analyze the latest debug screenshot to find this popup
img = Image.open('Captures/parcels/debug_original_220056.png')
arr = np.array(img)

print(f"Screenshot dimensions: {img.width}x{img.height}")

# The popup background is lighter than the page
# Looking for the lighter beige/tan color in the text area
# The attachment shows colors around RGB(250-255, 200-220, 160-180)

# Scan for popup text area (lighter beige color)
beige_lower = np.array([245, 195, 155])
beige_upper = np.array([255, 225, 185])

beige_mask = np.all((arr >= beige_lower) & (arr <= beige_upper), axis=2)
beige_pixels = np.sum(beige_mask)
print(f"\nBeige text area pixels: {beige_pixels}")

if beige_pixels > 100:
    coords = np.argwhere(beige_mask)
    min_y, max_y = coords[:, 0].min(), coords[:, 0].max()
    min_x, max_x = coords[:, 1].min(), coords[:, 1].max()
    width = max_x - min_x
    height = max_y - min_y
    print(f"Beige area bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"Beige area dimensions: {width}x{height}")
    
    # The popup also includes the dark icon to the left
    # Add ~40 pixels to the left
    popup_left = max(0, min_x - 45)
    popup_top = min_y
    popup_right = max_x
    popup_bottom = max_y
    
    popup_width = popup_right - popup_left
    popup_height = popup_bottom - popup_top
    
    print(f"\nFull popup (including icon): ({popup_left}, {popup_top}) to ({popup_right}, {popup_bottom})")
    print(f"Full popup dimensions: {popup_width}x{popup_height}")
    
    # Crop and save
    popup_img = img.crop((popup_left, popup_top, popup_right, popup_bottom))
    popup_img.save('test_beige_detection.png')
    print(f"\n✓ Saved test crop: {popup_img.width}x{popup_img.height}")
