#!/usr/bin/env python3
"""
Better split of config_utils.py - analyzes structure and splits logically.
Preserves ALL code including comments.
"""

from pathlib import Path
import re

source_file = Path(r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py")

with open(source_file, 'r', encoding='utf-8') as f:
    content = f.read()
    lines = content.split('\n')

print(f"Total lines: {len(lines)}")

# Find major section boundaries
print("\nAnalyzing structure...")

# Find where CFG and constants are defined
cfg_line = None
for i, line in enumerate(lines):
    if 'PKG_DIR = Path(__file__)' in line:
        cfg_line = i
        print(f"Found CFG section at line {i+1}")
        break

# Find where session management starts
session_line = None  
for i, line in enumerate(lines):
    if 'Simple local session for login' in line:
        session_line = i
        print(f"Found Session management at line {i+1}")
        break

# Find where login dialog starts
login_line = None
for i, line in enumerate(lines):
    if 'def show_login_dialog' in line:
        login_line = i
        print(f"Found Login dialog at line {i+1}")
        break

# Find where SplashScreen class starts
splash_line = None
for i, line in enumerate(lines):
    if 'class SplashScreen:' in line:
        splash_line = i
        print(f"Found SplashScreen class at line {i+1}")
        break

# Find where OldCompactHUD class starts
hud_line = None
for i, line in enumerate(lines):
    if 'class OldCompactHUD:' in line:
        hud_line = i
        print(f"Found OldCompactHUD class at line {i+1}")
        break

# Find where hud_start() function is (after the class)
hud_funcs_line = None
for i, line in enumerate(lines):
    if 'def hud_start():' in line:
        hud_funcs_line = i
        print(f"Found hud_start() at line {i+1}")
        break

# Find where helper functions start
helpers_line = None
for i, line in enumerate(lines):
    if 'def ensure_dir(p: Path):' in line:
        helpers_line = i
        print(f"Found helper functions at line {i+1}")
        break

print("\n" + "="*60)
print("SUGGESTED SPLIT PLAN:")
print("="*60)
print(f"\n1. config_core.py (lines 1-{session_line})")
print(f"   - Imports, constants, CFG, logging")
print(f"\n2. config_auth.py (lines {session_line+1}-{splash_line})")
print(f"   - Session management, login dialog")
print(f"\n3. config_splash.py (lines {splash_line+1}-{hud_line})")
print(f"   - SplashScreen class")
print(f"\n4. config_hud.py (lines {hud_line+1}-{hud_funcs_line})")
print(f"   - OldCompactHUD class (main UI)")
print(f"\n5. config_hud_api.py (lines {hud_funcs_line+1}-{helpers_line})")
print(f"   - HUD API functions (hud_start, hud_push, etc.)")
print(f"\n6. config_helpers.py (lines {helpers_line+1}-{len(lines)})")
print(f"   - Helper functions")

print("\n\nProceed with this split? This preserves ALL code.")
