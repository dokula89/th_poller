from PIL import Image
import numpy as np

# Load the screenshot
img = Image.open('Captures/parcels/debug_original_220844.png')
arr = np.array(img)

print(f'Image size: {img.size}')

# Check for NEW popup color RGB(255, 155, 0)
mask = (
    (arr[:,:,0] >= 250) & (arr[:,:,0] <= 255) &
    (arr[:,:,1] >= 150) & (arr[:,:,1] <= 160) &
    (arr[:,:,2] >= 0) & (arr[:,:,2] <= 5)
)

coords = np.argwhere(mask)
print(f'Found {len(coords)} pixels matching RGB(255, 155, 0) range')

if len(coords) > 100:
    # Get bounding box
    min_y = coords[:, 0].min()
    max_y = coords[:, 0].max()
    min_x = coords[:, 1].min()
    max_x = coords[:, 1].max()
    
    print(f'Popup bounds: ({min_x}, {min_y}) to ({max_x}, {max_y})')
    print(f'Popup size: {max_x - min_x}x{max_y - min_y} pixels')
    
    # Crop and save
    popup = img.crop((min_x - 5, min_y - 5, max_x + 5, max_y + 5))
    popup.save('Captures/parcels/test_popup_crop.png')
    print('Saved cropped popup to test_popup_crop.png')
else:
    print('Not enough pixels found - popup detection will fail')

