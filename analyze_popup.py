"""
Analyze the popup in the screenshot to find exact colors and bounds
"""

from PIL import Image
import numpy as np
from pathlib import Path

# Load the debug image
image_path = Path(__file__).parent / "Captures" / "parcels" / "debug_original_215542.png"
image = Image.open(image_path)
img_array = np.array(image)

print(f"Image size: {image.width}x{image.height}")
print(f"Image shape: {img_array.shape}")

# Sample the popup area manually (from your screenshot, it appears around x=640-860, y=280-460)
# Let's sample a few pixels to get the exact color
popup_sample_x = 750  # Middle of popup
popup_sample_y = 350  # Middle of popup

# Get color at that point
sample_color = img_array[popup_sample_y, popup_sample_x]
print(f"\nSample color at ({popup_sample_x}, {popup_sample_y}): RGB{tuple(sample_color)}")

# Try different color ranges to find the popup
print("\n=== Testing different color masks ===")

# Test 1: Light tan/beige (the popup background)
tan_mask = (
    (img_array[:, :, 0] > 230) & (img_array[:, :, 0] < 255) &  # Red
    (img_array[:, :, 1] > 210) & (img_array[:, :, 1] < 235) &  # Green
    (img_array[:, :, 2] > 170) & (img_array[:, :, 2] < 200)    # Blue
)
tan_coords = np.argwhere(tan_mask)
if len(tan_coords) > 0:
    min_y = tan_coords[:, 0].min()
    max_y = tan_coords[:, 0].max()
    min_x = tan_coords[:, 1].min()
    max_x = tan_coords[:, 1].max()
    print(f"\nTan mask found: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"  Size: {max_x - min_x}x{max_y - min_y} pixels")
    print(f"  Pixel count: {len(tan_coords)}")
    
    # Crop and save
    popup_img = image.crop((min_x, min_y, max_x, max_y))
    output_path = Path(__file__).parent / "Captures" / "parcels" / "extracted_popup.png"
    popup_img.save(output_path)
    print(f"  Saved to: {output_path}")
else:
    print("Tan mask: No pixels found")

# Test 2: Broader tan range
print("\n--- Trying broader tan range ---")
broad_tan_mask = (
    (img_array[:, :, 0] > 220) & (img_array[:, :, 0] < 255) &  # Red
    (img_array[:, :, 1] > 200) & (img_array[:, :, 1] < 240) &  # Green
    (img_array[:, :, 2] > 160) & (img_array[:, :, 2] < 210)    # Blue
)
broad_tan_coords = np.argwhere(broad_tan_mask)
if len(broad_tan_coords) > 0:
    min_y = broad_tan_coords[:, 0].min()
    max_y = broad_tan_coords[:, 0].max()
    min_x = broad_tan_coords[:, 1].min()
    max_x = broad_tan_coords[:, 1].max()
    print(f"Broad tan mask found: ({min_x}, {min_y}) to ({max_x}, {max_y})")
    print(f"  Size: {max_x - min_x}x{max_y - min_y} pixels")
    print(f"  Pixel count: {len(broad_tan_coords)}")
    
    # Crop and save
    popup_img2 = image.crop((min_x, min_y, max_x, max_y))
    output_path2 = Path(__file__).parent / "Captures" / "parcels" / "extracted_popup_broad.png"
    popup_img2.save(output_path2)
    print(f"  Saved to: {output_path2}")
else:
    print("Broad tan mask: No pixels found")

# Test 3: Sample actual colors from the popup area
print("\n--- Sampling colors from popup area (estimated at x=640-860, y=280-460) ---")
popup_region = img_array[280:460, 640:860]
unique_colors = np.unique(popup_region.reshape(-1, popup_region.shape[2]), axis=0)
print(f"Unique colors in popup region: {len(unique_colors)}")
print("First 10 unique colors:")
for i, color in enumerate(unique_colors[:10]):
    print(f"  RGB{tuple(color)}")

# Find the most common color (likely the background)
colors_reshaped = popup_region.reshape(-1, 3)
unique, counts = np.unique(colors_reshaped, axis=0, return_counts=True)
most_common_idx = counts.argmax()
most_common_color = unique[most_common_idx]
print(f"\nMost common color in popup area: RGB{tuple(most_common_color)} ({counts[most_common_idx]} pixels)")

print("\n=== Manual crop at estimated location ===")
manual_popup = image.crop((640, 280, 860, 460))
manual_output = Path(__file__).parent / "Captures" / "parcels" / "extracted_popup_manual.png"
manual_popup.save(manual_output)
print(f"Saved manual crop to: {manual_output}")
print(f"Manual crop size: {manual_popup.width}x{manual_popup.height}")
