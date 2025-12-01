"""Detect popup by matching the small icon template"""
from PIL import Image
import numpy as np
from pathlib import Path

# Load the template (small icon)
template_path = Path('path_to_small_icon.png')  # UPDATE THIS PATH
if not template_path.exists():
    print("ERROR: Please provide the path to the small icon image")
    print("Usage: Update template_path in this script")
    exit(1)

template = Image.open(template_path)
template_arr = np.array(template)
template_h, template_w = template_arr.shape[:2]

print(f"Template size: {template_w}x{template_h}")

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
screen_h, screen_w = screen_arr.shape[:2]

print(f"Screenshot size: {screen_w}x{screen_h}")
print(f"Searching for template...")

# Slide the template across the screenshot
best_match_score = float('inf')
best_match_pos = None

for y in range(screen_h - template_h + 1):
    for x in range(screen_w - template_w + 1):
        # Extract region
        region = screen_arr[y:y+template_h, x:x+template_w]
        
        # Calculate difference (sum of absolute differences)
        diff = np.sum(np.abs(region.astype(int) - template_arr.astype(int)))
        
        if diff < best_match_score:
            best_match_score = diff
            best_match_pos = (x, y)
    
    # Progress indicator
    if y % 50 == 0:
        print(f"  Scanning row {y}/{screen_h}...")

print(f"\n✓ Best match found at: {best_match_pos}")
print(f"  Match score: {best_match_score}")
print(f"  Template top-left: ({best_match_pos[0]}, {best_match_pos[1]})")
print(f"  Template bottom-right: ({best_match_pos[0] + template_w}, {best_match_pos[1] + template_h})")

# The popup extends to the right and down from the icon
# Based on your attachment, popup is roughly 220 wide x 140 tall
popup_left = best_match_pos[0]
popup_top = best_match_pos[1]
popup_right = popup_left + 220  # Approximate width
popup_bottom = popup_top + 140  # Approximate height

print(f"\nEstimated popup coordinates:")
print(f"  Top-left: ({popup_left}, {popup_top})")
print(f"  Bottom-right: ({popup_right}, {popup_bottom})")
print(f"  Dimensions: {popup_right - popup_left}x{popup_bottom - popup_top}")

# Save the detected popup
popup_crop = screenshot.crop((popup_left, popup_top, popup_right, popup_bottom))
popup_crop.save('detected_popup_template.png')
print(f"\n✓ Saved detected popup to: detected_popup_template.png")
