#!/usr/bin/env python3
# Test script to open address match window directly

import sys
import traceback
from pathlib import Path

# Add logging
DEBUG_LOG = Path(__file__).parent / "test_address_match.log"

def log(msg):
    print(msg)
    with open(DEBUG_LOG, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")

log("=== Test Address Match Window ===")
log(f"Log file: {DEBUG_LOG}")

try:
    log("Importing tkinter...")
    import tkinter as tk
    log("✓ tkinter imported")
    
    log("Creating root window...")
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    log("✓ root window created")
    
    log("Importing config_helpers...")
    from config_helpers import show_address_match_window
    log("✓ config_helpers imported")
    
    log("Calling show_address_match_window(1, root)...")
    show_address_match_window(1, root)
    log("✓ show_address_match_window returned")
    
    log("Starting mainloop...")
    root.mainloop()
    log("✓ mainloop exited")
    
except Exception as e:
    log(f"❌ ERROR: {e}")
    log(f"Traceback:\n{traceback.format_exc()}")
    sys.exit(1)

log("=== Test Complete ===")
