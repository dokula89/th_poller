"""
Test logout flow - verify login dialog appears when logout is clicked
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk
from config_utils import show_login_dialog, _clear_session, _save_session, log_to_file
import time

def test_logout_flow():
    """Simulates the logout flow to verify login dialog appears"""
    print("=== Testing Logout Flow ===\n")
    
    # Create a root window (simulating the HUD)
    root = tk.Tk()
    root.title("Test HUD")
    root.geometry("300x150")
    
    # Create initial session
    _save_session("daniel", time.time() + 24*60*60)
    print("✓ Created test session")
    
    label = tk.Label(root, text="Click 'Test Logout' to simulate logout button click", 
                     wraplength=250, pady=20)
    label.pack()
    
    def simulate_logout():
        """Simulates what happens when logout is clicked"""
        print("\n--- Logout clicked ---")
        
        # Clear session
        _clear_session()
        print("✓ Session cleared")
        log_to_file("[Test] Logout clicked - clearing session")
        
        # Hide HUD
        try:
            root.withdraw()
            root.update()
            print("✓ HUD hidden")
            log_to_file("[Test] HUD hidden")
        except Exception as e:
            print(f"✗ Error hiding HUD: {e}")
        
        # Force process pending events
        try:
            root.update_idletasks()
        except Exception:
            pass
        
        # Show login dialog
        print("✓ Showing login dialog...")
        log_to_file("[Test] Showing login dialog after logout")
        ok_login = show_login_dialog(root)
        log_to_file(f"[Test] Login result: {ok_login}")
        
        if ok_login:
            # Restore HUD
            print(f"✓ Login successful, restoring HUD")
            try:
                root.deiconify()
                root.lift()
                root.focus_force()
                root.update()
                label.config(text="Logged back in! You can close this window.")
                print("✓ HUD restored")
            except Exception as e:
                print(f"✗ Error showing HUD: {e}")
        else:
            # User canceled
            print("✗ Login canceled - would quit app")
            log_to_file("[Test] Login canceled - quitting app")
            root.destroy()
    
    logout_btn = tk.Button(root, text="Test Logout", command=simulate_logout,
                          bg="#DC3545", fg="white", font=("Segoe UI", 10, "bold"),
                          padx=20, pady=6)
    logout_btn.pack(pady=10)
    
    print("\nGUI window opened. Click 'Test Logout' to test the flow.")
    print("Expected behavior:")
    print("1. HUD window should hide")
    print("2. Login dialog should appear on top")
    print("3. After login, HUD should restore")
    print("\nCheck debug_queue.log for detailed [Test] log entries.\n")
    
    root.mainloop()

if __name__ == "__main__":
    test_logout_flow()
