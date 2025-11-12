"""
Test script to verify the insert DB window opens and works correctly.
"""
import tkinter as tk
from config_utils import show_insert_db_window, log_to_file

# Test job ID - change this to match your actual job
TEST_JOB_ID = 1

log_to_file("="*80)
log_to_file("TEST: Starting insert DB window test")
log_to_file("="*80)

# Create a minimal Tk window
root = tk.Tk()
root.withdraw()  # Hide the root window

# Try to open the insert DB window
try:
    log_to_file(f"TEST: Calling show_insert_db_window with job_id={TEST_JOB_ID}")
    show_insert_db_window(TEST_JOB_ID, root)
    log_to_file("TEST: Window function returned successfully")
    
    # Keep the window open
    root.mainloop()
except Exception as e:
    log_to_file(f"TEST ERROR: {e}")
    import traceback
    log_to_file(traceback.format_exc())
    print(f"Error: {e}")
    print(traceback.format_exc())
