"""Extract popup from the latest screenshot"""
from PIL import Image
from pathlib import Path

# The template matching found the icon at (647, 287)
# Popup is 220x140 starting from that position

# Find the latest parcel screenshot
captures_dir = Path('Captures/parcels')
screenshots = sorted(captures_dir.glob('parcel_*.png'))

if not screenshots:
    print("No screenshots found!")
    exit(1)

latest = screenshots[-1]
print(f"Processing: {latest.name}")

# Load screenshot
img = Image.open(latest)
print(f"Screenshot size: {img.width}x{img.height}")

# Extract popup at known coordinates
popup_left = 647
popup_top = 287
popup_right = popup_left + 220
popup_bottom = popup_top + 140

print(f"Extracting popup: ({popup_left}, {popup_top}) to ({popup_right}, {popup_bottom})")

# Crop the popup
popup = img.crop((popup_left, popup_top, popup_right, popup_bottom))

# Save to captures/parcels folder
output_path = captures_dir / f"extracted_popup_{latest.stem}.png"
popup.save(output_path)

print(f"✓ Saved popup: {output_path}")
print(f"  Size: {popup.width}x{popup.height}")
