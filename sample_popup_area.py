#!/usr/bin/env python3
"""
Sample colors from where I can see the popup in the screenshot
Based on the attachment, popup is around x=640-860, y=280-460
"""
from PIL import Image
import numpy as np

img = Image.open('Captures/parcels/debug_original_215247.png')
img_array = np.array(img)

# Sample from the popup area visible in the screenshot
popup_area = img_array[280:460, 640:860]

# Get unique colors and their counts
unique_colors = {}
for y in range(popup_area.shape[0]):
    for x in range(popup_area.shape[1]):
        color = tuple(popup_area[y, x])
        unique_colors[color] = unique_colors.get(color, 0) + 1

# Sort by frequency
sorted_colors = sorted(unique_colors.items(), key=lambda x: x[1], reverse=True)

print("Top 20 colors in popup area (sorted by frequency):")
for i, (color, count) in enumerate(sorted_colors[:20], 1):
    print(f"{i}. RGB{color}: {count} pixels")

# Also save a crop of that area to verify
popup_sample = img.crop((640, 280, 860, 460))
popup_sample.save('Captures/parcels/popup_sample_area.png')
print("\nSaved popup sample to popup_sample_area.png")
