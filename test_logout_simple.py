"""
Simple test to verify logout shows login dialog
Run this and click logout to see if the login dialog appears
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Start fresh with logging
with open("debug_queue.log", "w") as f:
    f.write("=== LOGOUT TEST STARTED ===\n")

import tkinter as tk
from config_utils import show_login_dialog, _clear_session, _save_session, log_to_file
import time

print("Creating test window...")

root = tk.Tk()
root.title("Logout Test")
root.geometry("400x200")

# Create a session first
_save_session("daniel", time.time() + 24*60*60)
print("Session created")

status_label = tk.Label(root, text="Session active. Click Logout to test.", 
                       font=("Segoe UI", 10), pady=20)
status_label.pack()

def on_logout():
    print("\n=== LOGOUT CLICKED ===")
    status_label.config(text="Logout clicked, clearing session...")
    root.update()
    
    # Clear session
    _clear_session()
    print("Session cleared")
    
    # Hide window
    print("Hiding main window...")
    root.withdraw()
    root.update()
    
    # Show login
    print("Calling show_login_dialog...")
    ok = show_login_dialog(root)
    print(f"Login result: {ok}")
    
    if ok:
        print("Login successful, showing window again")
        root.deiconify()
        root.lift()
        status_label.config(text="Logged back in!")
    else:
        print("Login canceled, closing app")
        root.destroy()

logout_btn = tk.Button(root, text="Logout", command=on_logout,
                      bg="#DC3545", fg="white", font=("Segoe UI", 11, "bold"),
                      padx=30, pady=10)
logout_btn.pack(pady=20)

print("\nWindow ready. Click 'Logout' button to test.")
print("Watch console and debug_queue.log for details.\n")

root.mainloop()
