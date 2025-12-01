from PIL import Image
import numpy as np

# Load the screenshot
img = Image.open('Captures/parcels/debug_original_220844.png')
arr = np.array(img)

print(f'Image size: {img.size}')

# Look for dark text pixels
text_mask = (arr.sum(axis=2) < 200)
text_coords = np.argwhere(text_mask)

print(f'Found {len(text_coords)} text pixels total')

# Filter to right half
right_half_x = img.width // 2
right_coords = text_coords[text_coords[:, 1] >= right_half_x]

print(f'Found {len(right_coords)} text pixels in right half (x >= {right_half_x})')

if len(right_coords) >= 50:
    # Get bounding box
    min_y = right_coords[:, 0].min()
    max_y = right_coords[:, 0].max()
    min_x = right_coords[:, 1].min()
    max_x = right_coords[:, 1].max()
    
    print(f'Text bounding box: ({min_x}, {min_y}) to ({max_x}, {max_y})')
    print(f'Text region size: {max_x - min_x}x{max_y - min_y} pixels')
    
    # Add padding
    padding = 20
    popup_left = max(0, min_x - padding)
    popup_top = max(0, min_y - padding)
    popup_right = min(img.width, max_x + padding)
    popup_bottom = min(img.height, max_y + padding)
    
    print(f'With padding: ({popup_left}, {popup_top}) to ({popup_right}, {popup_bottom})')
    
    # Crop and save
    popup = img.crop((popup_left, popup_top, popup_right, popup_bottom))
    popup.save('Captures/parcels/test_text_based_crop.png')
    print(f'\n✓ Saved cropped popup ({popup.width}x{popup.height}) to test_text_based_crop.png')
else:
    print('Not enough text pixels - detection would fail')
