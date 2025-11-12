#!/usr/bin/env python3
"""
Split config_utils.py into smaller, manageable files.
Target: ~2000 lines per file max
"""

def split_config_utils():
    with open('config_utils.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    print(f"Total lines: {total_lines}")
    
    # Find major class boundaries
    class_starts = []
    for i, line in enumerate(lines):
        if line.startswith('class '):
            class_name = line.split('class ')[1].split(':')[0].split('(')[0].strip()
            class_starts.append((i, class_name))
            print(f"Found class at line {i+1}: {class_name}")
    
    # Split strategy:
    # File 1 (config_core.py): Lines 1-478 - imports, helper functions, login dialog
    # File 2 (config_splash.py): Lines 478-568 - SplashScreen class
    # File 3 (config_hud.py): Lines 568-7283 - OldCompactHUD class (main UI)
    # File 4 (config_helpers.py): Lines 7283-7686 - HUD helper functions
    # File 5 (config_windows.py): Lines 7686-end - Address Match & Insert DB windows
    
    # Read imports from original file
    imports_end = 0
    for i, line in enumerate(lines):
        if line.startswith(('import ', 'from ')) or line.strip().startswith('#'):
            imports_end = i + 1
        elif line.strip() and not line.strip().startswith('#'):
            break
    
    imports_block = ''.join(lines[:imports_end])
    
    # Split points
    splits = [
        ('config_core.py', 0, 478, 'Core utilities and login dialog'),
        ('config_splash.py', 478, 568, 'SplashScreen class'),
        ('config_hud.py', 568, 7283, 'OldCompactHUD main UI class'),
        ('config_helpers.py', 7283, 7686, 'HUD helper functions'),
        ('config_windows.py', 7686, total_lines, 'Address Match and Insert DB windows'),
    ]
    
    for filename, start, end, description in splits:
        print(f"\nCreating {filename} ({description})")
        print(f"  Lines {start+1} to {end} ({end-start} lines)")
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Write imports for non-core files
            if start > 0:
                f.write(imports_block)
                f.write('\n# Import core utilities\n')
                if filename != 'config_core.py':
                    f.write('from config_core import *\n')
                if filename == 'config_hud.py':
                    f.write('from config_splash import SplashScreen\n')
                if filename == 'config_windows.py':
                    f.write('from config_hud import OldCompactHUD\n')
                    f.write('from config_helpers import *\n')
                f.write('\n')
            
            # Write the content
            f.writelines(lines[start:end])
    
    # Create new main config_utils.py that imports everything
    with open('config_utils_new.py', 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('"""\n')
        f.write('config_utils.py - Main entry point (split into multiple files)\n')
        f.write('This file imports and re-exports everything from the split modules.\n')
        f.write('"""\n\n')
        f.write('# Import all modules\n')
        f.write('from config_core import *\n')
        f.write('from config_splash import *\n')
        f.write('from config_hud import *\n')
        f.write('from config_helpers import *\n')
        f.write('from config_windows import *\n')
        f.write('\n# Re-export everything\n')
        f.write('__all__ = []\n')
    
    print("\n✅ Split complete!")
    print("Created files:")
    for filename, _, _, desc in splits:
        print(f"  - {filename}: {desc}")
    print("  - config_utils_new.py: Main entry point")
    print("\nTo use the new structure:")
    print("1. Backup config_utils.py: mv config_utils.py config_utils_backup.py")
    print("2. Use new version: mv config_utils_new.py config_utils.py")

if __name__ == '__main__':
    split_config_utils()
