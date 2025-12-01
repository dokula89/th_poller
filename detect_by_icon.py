"""Detect popup by matching the parcel icon template"""
from PIL import Image
import numpy as np
from pathlib import Path
import cv2

# The icon is a small orange icon - I'll save it from the attachment
# For now, let me create a simple template matcher using the icon

# Load the screenshot
screenshot_path = Path('Captures/parcels/parcel_965_20251112_223903.png')
if not screenshot_path.exists():
    # Try to find any parcel screenshot
    screenshots = sorted(Path('Captures/parcels').glob('parcel_*.png'))
    if screenshots:
        screenshot_path = screenshots[-1]
    else:
        print("ERROR: No screenshots found")
        exit(1)

screenshot = Image.open(screenshot_path)
screen_arr = np.array(screenshot)

print(f"Screenshot size: {screenshot.width}x{screenshot.height}")

# The icon is approximately 16x16 pixels, dark orange color RGB(139, 75, 0) or similar
# Let's detect it by looking for dark orange squares

# Convert to RGB if needed
if len(screen_arr.shape) == 2:
    screen_arr = np.stack([screen_arr]*3, axis=2)

# Look for the dark orange icon color
# From the attachment, it appears to be RGB around (200, 100, 0) - darker orange
icon_lower = np.array([180, 80, 0])
icon_upper = np.array([220, 120, 20])

# Create mask
icon_mask = np.all((screen_arr >= icon_lower) & (screen_arr <= icon_upper), axis=2)
icon_pixels = np.sum(icon_mask)

print(f"Dark orange icon pixels found: {icon_pixels}")

if icon_pixels > 50:
    # Find the icon position
    coords = np.argwhere(icon_mask)
    min_y = coords[:, 0].min()
    max_y = coords[:, 0].max()
    min_x = coords[:, 1].min()
    max_x = coords[:, 1].max()
    
    icon_width = max_x - min_x
    icon_height = max_y - min_y
    
    print(f"\nIcon found at: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"Icon size: {icon_width}x{icon_height} pixels")
    
    # The popup extends from the icon
    # Based on your manual extraction: ~220 wide x 140 tall
    popup_left = min_x
    popup_top = min_y
    popup_right = min_x + 220
    popup_bottom = min_y + 140
    
    print(f"\nPopup coordinates:")
    print(f"  ({popup_left}, {popup_top}, {popup_right}, {popup_bottom})")
    print(f"  Dimensions: {popup_right - popup_left}x{popup_bottom - popup_top}")
    
    # Save the detected popup
    popup_crop = screenshot.crop((popup_left, popup_top, popup_right, popup_bottom))
    popup_crop.save('detected_popup_by_icon.png')
    print(f"\n✓ Saved to: detected_popup_by_icon.png ({popup_crop.width}x{popup_crop.height})")
    
    # Also save just the icon
    icon_crop = screenshot.crop((min_x, min_y, max_x, max_y))
    icon_crop.save('detected_icon.png')
    print(f"✓ Saved icon to: detected_icon.png ({icon_crop.width}x{icon_crop.height})")
else:
    print("ERROR: Icon not found!")
    print("Trying to detect by scanning for small orange regions...")
    
    # Alternative: find compact orange regions
    from scipy import ndimage
    labeled, num_features = ndimage.label(icon_mask)
    
    if num_features > 0:
        print(f"Found {num_features} orange regions")
        # Find the most square-like region (likely the icon)
        for i in range(1, num_features + 1):
            region_coords = np.argwhere(labeled == i)
            r_min_y = region_coords[:, 0].min()
            r_max_y = region_coords[:, 0].max()
            r_min_x = region_coords[:, 1].min()
            r_max_x = region_coords[:, 1].max()
            r_width = r_max_x - r_min_x
            r_height = r_max_y - r_min_y
            
            # Icon should be roughly square and small (10-20 pixels)
            if 10 <= r_width <= 30 and 10 <= r_height <= 30:
                aspect_ratio = r_width / r_height
                if 0.7 <= aspect_ratio <= 1.3:  # Roughly square
                    print(f"  Region {i}: ({r_min_x}, {r_min_y}) size {r_width}x{r_height}")
