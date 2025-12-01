"""Use template matching with the icon image"""
from PIL import Image
import numpy as np
from pathlib import Path

# First, I need to save the icon attachment as a file
# The user sent a small orange icon - let me create it from the screenshot by sampling

screenshot_path = Path('Captures/parcels/parcel_965_20251112_223903.png')
if not screenshot_path.exists():
    screenshots = sorted(Path('Captures/parcels').glob('parcel_*.png'))
    if screenshots:
        screenshot_path = screenshots[-1]
    else:
        print("ERROR: No screenshots found")
        exit(1)

screenshot = Image.open(screenshot_path)
print(f"Screenshot: {screenshot.width}x{screenshot.height}")

# Looking at the attachments, the icon appears at around (640-660, 280-300)
# Let me sample that area to create the template
# From the popup in the screenshot, I can see it's at approximately x=640, y=285

# The icon is the small dark orange square on the left of the popup
# Let me extract it manually from the known popup location
# Based on the screenshots, popup appears around (640, 285)

# Create a template from the icon area (approximately 15x15 pixels)
icon_x = 647  # Approximate from screenshots
icon_y = 287
icon_size = 16

# Extract the icon as template
try:
    template = screenshot.crop((icon_x, icon_y, icon_x + icon_size, icon_y + icon_size))
    template.save('popup_icon_template.png')
    print(f"✓ Saved template: {template.width}x{template.height}")
    
    # Now use template matching
    template_arr = np.array(template)
    screen_arr = np.array(screenshot)
    
    template_h, template_w = template_arr.shape[:2]
    screen_h, screen_w = screen_arr.shape[:2]
    
    print(f"\nSearching for {template_w}x{template_h} template in {screen_w}x{screen_h} screenshot...")
    
    # Simple template matching - find best match
    best_score = float('inf')
    best_pos = None
    
    # Only search in likely areas (not the entire screen for speed)
    # Popup typically appears in center-right area
    search_x_start = 400
    search_x_end = 900
    search_y_start = 200
    search_y_end = 550
    
    for y in range(search_y_start, min(search_y_end, screen_h - template_h + 1)):
        for x in range(search_x_start, min(search_x_end, screen_w - template_w + 1)):
            region = screen_arr[y:y+template_h, x:x+template_w]
            
            # Calculate sum of squared differences
            diff = np.sum((region.astype(float) - template_arr.astype(float)) ** 2)
            
            if diff < best_score:
                best_score = diff
                best_pos = (x, y)
        
        if y % 10 == 0:
            progress = (y - search_y_start) / (search_y_end - search_y_start) * 100
            print(f"  Progress: {progress:.0f}%")
    
    print(f"\n✓ Icon found at: ({best_pos[0]}, {best_pos[1]})")
    print(f"  Match score: {best_score}")
    
    # The popup extends from the icon
    # Icon is top-left of the popup box
    popup_left = best_pos[0]
    popup_top = best_pos[1]
    popup_right = popup_left + 220  # Standard popup width
    popup_bottom = popup_top + 140  # Standard popup height
    
    print(f"\nPopup coordinates:")
    print(f"  Left: {popup_left}")
    print(f"  Top: {popup_top}")
    print(f"  Right: {popup_right}")
    print(f"  Bottom: {popup_bottom}")
    print(f"  Dimensions: {popup_right - popup_left}x{popup_bottom - popup_top}")
    
    # Extract and save
    popup_crop = screenshot.crop((popup_left, popup_top, popup_right, popup_bottom))
    popup_crop.save('detected_popup_template_match.png')
    print(f"\n✓ Saved popup: detected_popup_template_match.png ({popup_crop.width}x{popup_crop.height})")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
