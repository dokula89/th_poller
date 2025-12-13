#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Queue Poller - Cross-Platform Launcher
Detects OS and launches appropriately, showing instructions for Mac users.
"""

import sys
import os
import platform
import subprocess
from pathlib import Path

def get_script_dir():
    """Get the directory where this script is located"""
    return Path(__file__).parent.absolute()

def show_mac_instructions():
    """Show Mac setup instructions popup and open the guide file"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        
        root = tk.Tk()
        root.withdraw()
        
        # Get the guide file path
        script_dir = get_script_dir()
        guide_file = script_dir / "MAC_SETUP_GUIDE.txt"
        
        message = """Welcome to Queue Poller on Mac!

To run this application, you need to:

1. Open Terminal
2. Navigate to the Queue Poller folder
3. Run: chmod +x start_mac.sh
4. Run: ./start_mac.sh

The Mac Setup Guide will now open with detailed instructions.

Prerequisites:
• Python 3 (brew install python3)
• Tesseract (brew install tesseract)
• Git (brew install git)

Would you like to open the setup guide now?"""
        
        result = messagebox.askyesno(
            "Queue Poller - Mac Setup",
            message,
            icon='info'
        )
        
        if result and guide_file.exists():
            # Open the guide file with default text editor
            subprocess.run(["open", str(guide_file)])
        
        root.destroy()
        
        # Also try to open Terminal in the correct directory
        try:
            terminal_script = f'''
            tell application "Terminal"
                activate
                do script "cd '{script_dir}' && echo 'Queue Poller Directory' && echo 'Run: chmod +x start_mac.sh && ./start_mac.sh'"
            end tell
            '''
            subprocess.run(["osascript", "-e", terminal_script])
        except Exception:
            pass
            
    except ImportError:
        # tkinter not available, print to console
        print("\n" + "="*60)
        print("QUEUE POLLER - MAC SETUP REQUIRED")
        print("="*60)
        print("""
To run Queue Poller on Mac:

1. Install prerequisites:
   brew install python3 python-tk tesseract git

2. Navigate to this folder in Terminal:
   cd {}

3. Make the start script executable:
   chmod +x start_mac.sh

4. Run the application:
   ./start_mac.sh

See MAC_SETUP_GUIDE.txt for detailed instructions.
""".format(get_script_dir()))
        print("="*60 + "\n")
        
        # Try to open the guide
        guide_file = get_script_dir() / "MAC_SETUP_GUIDE.txt"
        if guide_file.exists():
            subprocess.run(["open", str(guide_file)])

def run_on_windows():
    """Run the application on Windows"""
    script_dir = get_script_dir()
    
    # Check for virtual environment
    venv_python = script_dir / ".venv" / "Scripts" / "python.exe"
    
    if venv_python.exists():
        python_exe = str(venv_python)
    else:
        python_exe = sys.executable
    
    # Run the main poller script
    run_poller = script_dir / "run_poller.py"
    if run_poller.exists():
        subprocess.run([python_exe, str(run_poller)], cwd=script_dir)
    else:
        print("Error: run_poller.py not found")
        sys.exit(1)

def run_on_mac():
    """Run the application on Mac"""
    script_dir = get_script_dir()
    
    # Check if running from Terminal (has proper environment)
    # or from Finder (needs setup instructions)
    
    # Check for virtual environment
    venv_python = script_dir / ".venv" / "bin" / "python3"
    
    if not venv_python.exists():
        # No venv - show setup instructions
        show_mac_instructions()
        return
    
    # Check if dependencies are installed
    try:
        result = subprocess.run(
            [str(venv_python), "-c", "import tkinter; import mysql.connector"],
            capture_output=True,
            timeout=10
        )
        if result.returncode != 0:
            show_mac_instructions()
            return
    except Exception:
        show_mac_instructions()
        return
    
    # All good - run the app
    run_poller = script_dir / "run_poller.py"
    if run_poller.exists():
        subprocess.run([str(venv_python), str(run_poller)], cwd=script_dir)
    else:
        print("Error: run_poller.py not found")
        show_mac_instructions()

def run_on_linux():
    """Run the application on Linux"""
    script_dir = get_script_dir()
    
    # Similar to Mac
    venv_python = script_dir / ".venv" / "bin" / "python3"
    
    if venv_python.exists():
        python_exe = str(venv_python)
    else:
        python_exe = "python3"
    
    run_poller = script_dir / "run_poller.py"
    if run_poller.exists():
        subprocess.run([python_exe, str(run_poller)], cwd=script_dir)
    else:
        print("Error: run_poller.py not found")
        sys.exit(1)

def main():
    """Main entry point - detect OS and run appropriately"""
    system = platform.system()
    
    print(f"Queue Poller Launcher")
    print(f"OS: {system}")
    print(f"Python: {sys.version}")
    print(f"Directory: {get_script_dir()}")
    print("-" * 40)
    
    if system == "Windows":
        run_on_windows()
    elif system == "Darwin":  # macOS
        run_on_mac()
    elif system == "Linux":
        run_on_linux()
    else:
        print(f"Unsupported operating system: {system}")
        sys.exit(1)

if __name__ == "__main__":
    main()
