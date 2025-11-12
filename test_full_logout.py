"""
Complete logout test with HUD simulation
This mimics exactly what happens in the real app
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("Starting comprehensive logout test...")
print("This will:")
print("1. Create a HUD window")
print("2. You click Logout")
print("3. HUD hides, login dialog appears")
print("4. Sign in to restore HUD")
print("")

import tkinter as tk
from config_utils import OldCompactHUD, ensure_session_before_hud, log_to_file
import queue

# Clear log
with open("debug_queue.log", "w") as f:
    f.write("=== COMPREHENSIVE LOGOUT TEST ===\n")

# Create root
root = tk.Tk()
root.withdraw()  # Start hidden

# Check session
print("Checking for existing session...")
if not ensure_session_before_hud(root):
    print("No session or login canceled - exiting")
    root.destroy()
    sys.exit(0)

print("Session valid, creating HUD...")

# Create HUD
inbox = queue.Queue()
hud = OldCompactHUD(root, inbox)
print("HUD created!")
print("")
print("=" * 50)
print("INSTRUCTIONS:")
print("=" * 50)
print("1. The HUD window should be visible now")
print("2. Click the RED 'Logout' button in the top-right")
print("3. The HUD should disappear")
print("4. A login dialog should appear immediately")
print("5. Sign in (daniel / Teller89*)")
print("6. The HUD should reappear")
print("")
print("Check debug_queue.log for detailed [Auth] messages")
print("=" * 50)
print("")

root.mainloop()
print("Test ended")
