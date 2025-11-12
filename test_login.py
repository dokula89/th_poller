"""
Test the updated login flow with:
1. Dark background (#0D1117)
2. Sign In button
3. Stay logged in checkbox
4. Session handling
"""
import sys
import os
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from config_utils import show_login_dialog, _session_valid, _clear_session, _load_session
import tkinter as tk

def test_login():
    """Test the login dialog"""
    print("\n" + "="*60)
    print("LOGIN DIALOG TEST")
    print("="*60)
    
    # Create a dummy root for the login dialog
    root = tk.Tk()
    root.withdraw()  # Hide the dummy root
    
    # Clear any existing session
    _clear_session()
    print("✓ Cleared existing session")
    
    # Show login dialog
    print("\n📋 Opening login dialog...")
    print("   - Background should be dark (#0D1117)")
    print("   - Should have 'Sign In' button (green #238636)")
    print("   - Should have 'Cancel' button")
    print("   - Should have 'Stay logged in for 24 hours' checkbox")
    print("\nTest credentials: daniel / Teller89*")
    
    success = show_login_dialog(root)
    
    print("\n" + "="*60)
    if success:
        print("✓ LOGIN SUCCESSFUL!")
        
        # Check session
        if _session_valid():
            print("✓ Session is valid")
            
            # Load session details
            session = _load_session()
            if session:
                username = session.get('username', 'unknown')
                expires = session.get('expires', 0)
                remaining = expires - time.time()
                hours = remaining / 3600
                
                print(f"   Username: {username}")
                print(f"   Session expires in: {hours:.1f} hours")
                
                if hours >= 23.5:
                    print("   ✓ 24-hour session (checkbox was checked)")
                elif hours >= 0.5 and hours < 2:
                    print("   ✓ 1-hour session (checkbox was unchecked)")
                else:
                    print(f"   ⚠ Unexpected session length: {hours:.1f} hours")
        else:
            print("✗ Session is invalid (this shouldn't happen)")
    else:
        print("✗ LOGIN CANCELED OR FAILED")
        print("   This is expected if you clicked Cancel")
    
    print("="*60 + "\n")
    
    # Cleanup
    try:
        root.destroy()
    except:
        pass

if __name__ == "__main__":
    test_login()
