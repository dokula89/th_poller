"""
Test logout flow:
1. HUD should hide when logout is clicked
2. Login dialog should appear
3. HUD should restore if login succeeds
4. App should quit if login is canceled
"""
import sys
import os
import time
import tkinter as tk

sys.path.insert(0, os.path.dirname(__file__))

from config_utils import OldCompactHUD, _session_valid, _save_session, _clear_session

def test_logout():
    print("\n" + "="*60)
    print("LOGOUT FLOW TEST")
    print("="*60)
    
    # Create a valid session first
    _save_session("daniel", time.time() + 24*60*60)
    print("✓ Created test session")
    
    print("\nStarting HUD...")
    print("Instructions:")
    print("1. The HUD should appear with a 'Logout' button")
    print("2. Click 'Logout'")
    print("3. The HUD should HIDE")
    print("4. The login dialog should APPEAR")
    print("5. Try logging in again or cancel")
    print("\nStarting in 2 seconds...")
    time.sleep(2)
    
    # Create HUD
    hud = OldCompactHUD()
    hud.push("Test message - click Logout to test flow", "ok")
    
    # Run mainloop
    try:
        hud.run_mainloop_blocking()
    except Exception as e:
        print(f"\nHUD closed: {e}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    test_logout()
