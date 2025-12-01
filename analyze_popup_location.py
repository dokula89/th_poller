from PIL import Image
import numpy as np

# Load the screenshot
img = Image.open('Captures/parcels/debug_original_220844.png')
arr = np.array(img)

print(f'Image size: {img.size}')

# The popup has a distinct layout - it's a rectangular box
# Let's look for areas with high text density (dark pixels on orange)
# Look for dark text (low RGB values)
dark_mask = (arr.sum(axis=2) < 150)  # Dark pixels (text)

# Look for the orange background of popup (brighter than page background)
bright_orange = (
    (arr[:,:,0] >= 250) & 
    (arr[:,:,1] >= 150) & (arr[:,:,1] <= 160) &
    (arr[:,:,2] <= 5)
)

print(f'Found {bright_orange.sum()} bright orange pixels')

# Instead, let's look for the popup's distinctive feature:
# It appears as a lighter rectangle. Let's find rectangular regions
# Sample different areas
areas = [
    ("Top-left", (50, 50, 150, 150)),
    ("Popup area", (640, 280, 860, 460)),
    ("Right side", (900, 300, 1000, 400))
]

for name, coords in areas:
    sample = img.crop(coords)
    avg_color = np.array(sample).mean(axis=(0,1))
    print(f'{name}: Avg RGB({avg_color[0]:.0f}, {avg_color[1]:.0f}, {avg_color[2]:.0f})')

# Based on your manually extracted popup, let me check if there's a distinct boundary
# The popup seems to be in center-right area
# Let's just hard-code the expected popup region based on where it appeared before
print('\n If popup not detectable by color, using fixed region:')
print('  Popup expected at approximately (640, 280) to (860, 460)')
