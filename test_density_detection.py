from PIL import Image
import numpy as np

# Load the screenshot  
img = Image.open('Captures/parcels/debug_original_220844.png')
arr = np.array(img)

print(f'Image size: {img.size}')

# Look for dark text pixels
text_mask = (arr.sum(axis=2) < 200)

# EXCLUDE left sidebar (first 600 pixels)
sidebar_width = 600
text_mask[:, :sidebar_width] = False

text_coords = np.argwhere(text_mask)
print(f'Text pixels (excluding sidebar): {len(text_coords)}')

# Divide image into grid and find region with highest text density
grid_size = 50  # 50x50 pixel blocks
height, width = arr.shape[:2]

max_density = 0
best_region = None

for y in range(0, height - grid_size, grid_size//2):  # Overlapping blocks
    for x in range(sidebar_width, width - grid_size, grid_size//2):  # Start after sidebar
        region_mask = text_mask[y:y+grid_size, x:x+grid_size]
        density = region_mask.sum()
        if density > max_density:
            max_density = density
            best_region = (x, y)

print(f'Highest text density: {max_density} pixels in 50x50 block at {best_region}')

# From the best region, expand to find full popup extent
if best_region:
    center_x, center_y = best_region[0] + grid_size//2, best_region[1] + grid_size//2
    
    # Find all text within reasonable distance
    distances = np.sqrt((text_coords[:, 1] - center_x)**2 + (text_coords[:, 0] - center_y)**2)
    nearby = text_coords[distances < 150]  # Within 150 pixels of center
    
    if len(nearby) > 50:
        min_y = nearby[:, 0].min()
        max_y = nearby[:, 0].max()
        min_x = nearby[:, 1].min()
        max_x = nearby[:, 1].max()
        
        print(f'Nearby text region: ({min_x}, {min_y}) to ({max_x}, {max_y})')
        print(f'Size: {max_x - min_x}x{max_y - min_y}')
        
        # Add padding
        padding = 25
        popup_left = max(0, min_x - padding)
        popup_top = max(0, min_y - padding)
        popup_right = min(width, max_x + padding)
        popup_bottom = min(height, max_y + padding)
        
        # Crop and save
        popup = img.crop((popup_left, popup_top, popup_right, popup_bottom))
        popup.save('Captures/parcels/test_density_crop_v2.png')
        print(f'\n✓ Saved ({popup.width}x{popup.height}) to test_density_crop_v2.png')
