"""Detect popup coordinates in screenshot using template matching"""
from PIL import Image
import numpy as np
from pathlib import Path

def find_template(screenshot_path, template_path):
    """
    Find template image within screenshot using cross-correlation
    
    Args:
        screenshot_path: Path to full screenshot
        template_path: Path to popup template image
        
    Returns:
        tuple: (x, y, width, height) of popup location, or None if not found
    """
    # Load images
    screenshot = Image.open(screenshot_path)
    template = Image.open(template_path)
    
    # Convert to numpy arrays (grayscale for faster matching)
    screenshot_gray = np.array(screenshot.convert('L'))
    template_gray = np.array(template.convert('L'))
    
    screen_h, screen_w = screenshot_gray.shape
    template_h, template_w = template_gray.shape
    
    print(f"Screenshot: {screen_w}x{screen_h}")
    print(f"Template: {template_w}x{template_h}")
    
    if template_h > screen_h or template_w > screen_w:
        print("❌ Template is larger than screenshot!")
        return None
    
    # Normalize template for better matching
    template_normalized = template_gray.astype(np.float32)
    
    # Search for best match using sliding window
    best_score = -1
    best_pos = None
    
    print("\nSearching for template...")
    
    # Use stride to speed up search (every 5 pixels)
    stride = 5
    
    for y in range(0, screen_h - template_h + 1, stride):
        for x in range(0, screen_w - template_w + 1, stride):
            # Extract region
            region = screenshot_gray[y:y+template_h, x:x+template_w].astype(np.float32)
            
            # Calculate normalized cross-correlation
            # This is more robust than simple difference
            region_norm = region - np.mean(region)
            template_norm = template_normalized - np.mean(template_normalized)
            
            numerator = np.sum(region_norm * template_norm)
            denominator = np.sqrt(np.sum(region_norm**2) * np.sum(template_norm**2))
            
            if denominator > 0:
                score = numerator / denominator
            else:
                score = 0
            
            if score > best_score:
                best_score = score
                best_pos = (x, y)
        
        # Progress indicator
        if y % 50 == 0:
            print(f"  Scanning row {y}/{screen_h}... best score so far: {best_score:.3f}")
    
    if best_pos is None:
        print("❌ Template not found!")
        return None
    
    x, y = best_pos
    print(f"\n✓ Found template at: ({x}, {y})")
    print(f"  Match score: {best_score:.3f}")
    print(f"  Popup bounds: ({x}, {y}) to ({x + template_w}, {y + template_h})")
    print(f"  Popup dimensions: {template_w}x{template_h}")
    
    # Save visualization
    screenshot_rgb = screenshot.copy()
    from PIL import ImageDraw
    draw = ImageDraw.Draw(screenshot_rgb)
    draw.rectangle([x, y, x + template_w, y + template_h], outline='red', width=3)
    screenshot_rgb.save('popup_detected.png')
    print(f"\n✓ Saved visualization to: popup_detected.png")
    
    return (x, y, template_w, template_h)

if __name__ == "__main__":
    # Find the popup in the screenshot
    screenshot_path = "Captures/parcels/parcel_965_20251112_223903.png"
    
    # Use the most recent debug_popup as template
    popup_dir = Path("Captures/parcels")
    popups = sorted(popup_dir.glob("debug_popup_*.png"))
    
    if not popups:
        print("❌ No debug_popup files found! Run the automation first.")
        exit(1)
    
    template_path = popups[-1]
    print(f"Using template: {template_path.name}\n")
    
    result = find_template(screenshot_path, template_path)
    
    if result:
        x, y, w, h = result
        print(f"\n{'='*50}")
        print(f"POPUP COORDINATES:")
        print(f"  Top-left: ({x}, {y})")
        print(f"  Bottom-right: ({x + w}, {y + h})")
        print(f"  Size: {w}x{h}")
        print(f"{'='*50}")
