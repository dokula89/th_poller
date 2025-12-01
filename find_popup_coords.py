"""Detect popup coordinates in screenshot by color"""
from PIL import Image, ImageDraw
import numpy as np

# Load screenshot
screenshot_path = "Captures/parcels/parcel_965_20251112_223903.png"
img = Image.open(screenshot_path)
arr = np.array(img)

print(f"Screenshot: {img.width}x{img.height}")

# Detect beige text area (popup content)
lower_beige = np.array([245, 195, 155])
upper_beige = np.array([255, 225, 185])

beige_mask = np.all((arr >= lower_beige) & (arr <= upper_beige), axis=2)
beige_pixels = np.sum(beige_mask)

print(f"Beige pixels found: {beige_pixels}")

if beige_pixels > 100:
    coords = np.argwhere(beige_mask)
    min_y = coords[:, 0].min()
    max_y = coords[:, 0].max()
    min_x = coords[:, 1].min()
    max_x = coords[:, 1].max()
    
    # Add icon to the left
    icon_width = 45
    popup_left = max(0, min_x - icon_width)
    popup_top = min_y
    popup_right = max_x
    popup_bottom = max_y
    
    width = popup_right - popup_left
    height = popup_bottom - popup_top
    
    print(f"\n{'='*60}")
    print(f"POPUP DETECTED:")
    print(f"  Top-left corner: ({popup_left}, {popup_top})")
    print(f"  Bottom-right corner: ({popup_right}, {popup_bottom})")
    print(f"  Width x Height: {width}x{height} pixels")
    print(f"{'='*60}")
    
    # Save visualization
    img_copy = img.copy()
    draw = ImageDraw.Draw(img_copy)
    draw.rectangle([popup_left, popup_top, popup_right, popup_bottom], outline='red', width=3)
    img_copy.save('popup_detected.png')
    print(f"\n✓ Saved visualization to: popup_detected.png")
    
    # Also crop and save the popup
    popup = img.crop((popup_left, popup_top, popup_right, popup_bottom))
    popup.save('popup_cropped.png')
    print(f"✓ Saved cropped popup to: popup_cropped.png ({popup.width}x{popup.height})")
else:
    print("❌ Popup not found!")
