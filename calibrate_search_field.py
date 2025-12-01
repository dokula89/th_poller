"""
Parcel Automation Calibration Tool
Use this to find the exact coordinates of the search field
"""

import pyautogui
import time

print("=" * 60)
print("PARCEL AUTOMATION - SEARCH FIELD CALIBRATION")
print("=" * 60)
print()
print("Instructions:")
print("1. Open the King County Parcel Viewer in your browser")
print("2. Position browser window to right 80% of screen")
print("3. Hover your mouse over the ADDRESS SEARCH FIELD")
print("4. Press Ctrl+C when mouse is positioned")
print()
print("Waiting for you to position mouse...")
print("(Move mouse to search field, then press Ctrl+C)")
print()

try:
    while True:
        x, y = pyautogui.position()
        screen_width, screen_height = pyautogui.size()
        
        # Calculate percentages
        x_percent = (x / screen_width) * 100
        y_percent = (y / screen_height) * 100
        
        print(f"\rMouse Position: X={x} ({x_percent:.1f}%), Y={y} ({y_percent:.1f}%)    ", end='', flush=True)
        time.sleep(0.1)
        
except KeyboardInterrupt:
    print()
    print()
    print("=" * 60)
    print("COORDINATES CAPTURED!")
    print("=" * 60)
    
    x, y = pyautogui.position()
    screen_width, screen_height = pyautogui.size()
    
    x_percent = x / screen_width
    y_percent = y / screen_height
    
    print(f"Absolute Position: X={x}, Y={y}")
    print(f"Screen Size: {screen_width}x{screen_height}")
    print(f"Percentage: X={x_percent:.4f} ({x_percent*100:.2f}%), Y={y_percent:.4f} ({y_percent*100:.2f}%)")
    print()
    print("Update parcel_automation.py with these values:")
    print("-" * 60)
    print(f"search_field_x = int(screen_width * {x_percent:.4f})")
    print(f"search_field_y = int(screen_height * {y_percent:.4f})")
    print("-" * 60)
    print()
    print("Example code to add to enter_address() function:")
    print()
    print(f"    screen_width, screen_height = pyautogui.size()")
    print(f"    search_field_x = int(screen_width * {x_percent:.4f})")
    print(f"    search_field_y = int(screen_height * {y_percent:.4f})")
    print(f"    pyautogui.click(search_field_x, search_field_y)")
    print()
