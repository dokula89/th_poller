#!/usr/bin/env python3
"""
Start PHP built-in server for th_poller project
This allows accessing PHP files via http://localhost:8000/
"""
import subprocess
import sys
import os
from pathlib import Path

# Get the htdocs directory
HTDOCS_DIR = Path(__file__).parent / "htdocs"

if not HTDOCS_DIR.exists():
    print(f"Error: {HTDOCS_DIR} does not exist!")
    sys.exit(1)

print(f"Starting PHP server from: {HTDOCS_DIR}")
print(f"Server will be available at: http://localhost:8000/")
print(f"Press Ctrl+C to stop the server")
print("-" * 60)

try:
    # Start PHP built-in server
    subprocess.run([
        "php",
        "-S", "localhost:8000",
        "-t", str(HTDOCS_DIR)
    ])
except KeyboardInterrupt:
    print("\nServer stopped")
except FileNotFoundError:
    print("\nError: PHP executable not found in PATH")
    print("Please install PHP or add it to your PATH")
    sys.exit(1)
