#!/usr/bin/env python3
"""
Split config_utils.py into smaller files with better granularity.
Target: ~2000 lines per file max
"""

def split_config_utils_refined():
    with open('config_utils.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    print(f"Total lines: {total_lines}")
    
    # Find method boundaries in OldCompactHUD class
    in_class = False
    class_methods = []
    for i, line in enumerate(lines):
        if line.startswith('class OldCompactHUD'):
            in_class = True
            class_start = i
            print(f"OldCompactHUD class starts at line {i+1}")
        elif in_class and line.strip().startswith('def '):
            method_name = line.strip().split('def ')[1].split('(')[0]
            class_methods.append((i, method_name))
            if len(class_methods) <= 20:  # Print first 20
                print(f"  Method at line {i+1}: {method_name}")
        elif in_class and line.startswith('def ') and not line.startswith('    '):
            # Exited class
            in_class = False
            print(f"OldCompactHUD class ends around line {i}")
    
    # Read imports
    imports_end = 0
    for i, line in enumerate(lines):
        if line.startswith(('import ', 'from ')) or line.strip().startswith('#'):
            imports_end = i + 1
        elif line.strip() and not line.strip().startswith('#'):
            break
    
    imports_block = ''.join(lines[:imports_end])
    
    # Better split strategy based on actual content:
    # File 1: config_core.py (0-478) - imports, helpers, login
    # File 2: config_splash.py (478-568) - SplashScreen class  
    # File 3: config_hud_part1.py (568-2500) - OldCompactHUD init and early methods (~2000 lines)
    # File 4: config_hud_part2.py (2500-4500) - OldCompactHUD middle methods (~2000 lines)
    # File 5: config_hud_part3.py (4500-6500) - OldCompactHUD later methods (~2000 lines)
    # File 6: config_hud_part4.py (6500-7283) - OldCompactHUD final methods (~800 lines)
    # File 7: config_helpers.py (7283-7686) - HUD helper functions
    # File 8: config_windows.py (7686-end) - Address Match & Insert DB windows
    
    splits = [
        ('config_core.py', 0, 478, 'Core utilities and login dialog'),
        ('config_splash.py', 478, 568, 'SplashScreen class'),
        ('config_hud_part1.py', 568, 2500, 'OldCompactHUD class - Part 1 (init & early methods)'),
        ('config_hud_part2.py', 2500, 4500, 'OldCompactHUD class - Part 2 (middle methods)'),
        ('config_hud_part3.py', 4500, 6500, 'OldCompactHUD class - Part 3 (later methods)'),
        ('config_hud_part4.py', 6500, 7283, 'OldCompactHUD class - Part 4 (final methods)'),
        ('config_helpers.py', 7283, 7686, 'HUD helper functions'),
        ('config_windows.py', 7686, total_lines, 'Address Match and Insert DB windows'),
    ]
    
    print("\n" + "="*60)
    print("Creating split files...")
    print("="*60)
    
    for filename, start, end, description in splits:
        line_count = end - start
        print(f"\n📄 {filename}")
        print(f"   {description}")
        print(f"   Lines {start+1} to {end} ({line_count} lines)")
        
        with open(filename, 'w', encoding='utf-8') as f:
            # Write imports for non-core files
            if start > 0:
                f.write(imports_block)
                f.write('\n')
                f.write(f'# {description}\n')
                f.write('# This file is part of the split config_utils.py\n\n')
                
                # Add appropriate imports
                if 'part' not in filename:
                    f.write('from config_core import *\n')
                
                if filename == 'config_hud_part1.py':
                    f.write('from config_splash import SplashScreen\n')
                elif 'part' in filename:
                    # Parts 2-4 need part 1
                    part_num = int(filename.split('part')[1].split('.')[0])
                    for i in range(1, part_num):
                        f.write(f'# Note: This is a continuation of config_hud_part{i}.py\n')
                
                if filename == 'config_windows.py':
                    f.write('from config_core import *\n')
                    f.write('# Note: Uses OldCompactHUD from config_hud_part*.py\n')
                
                if filename == 'config_helpers.py':
                    f.write('from config_core import *\n')
                
                f.write('\n')
            
            # Write the content
            f.writelines(lines[start:end])
    
    # Create new main config_utils.py
    with open('config_utils_new.py', 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('"""\n')
        f.write('config_utils.py - Main entry point\n')
        f.write('Split into multiple files for better maintainability (each <2000 lines)\n')
        f.write('"""\n\n')
        f.write('# Import all split modules in order\n')
        f.write('from config_core import *\n')
        f.write('from config_splash import *\n')
        f.write('from config_hud_part1 import *\n')
        f.write('from config_hud_part2 import *\n')
        f.write('from config_hud_part3 import *\n')
        f.write('from config_hud_part4 import *\n')
        f.write('from config_helpers import *\n')
        f.write('from config_windows import *\n')
    
    print("\n" + "="*60)
    print("✅ Split complete!")
    print("="*60)
    print("\nCreated files:")
    for filename, start, end, desc in splits:
        print(f"  ✓ {filename} ({end-start} lines)")
    print(f"  ✓ config_utils_new.py (main entry point)")
    
    print("\n📋 To use the new structure:")
    print("1. Backup: Move config_utils.py to config_utils_backup.py")
    print("2. Activate: Move config_utils_new.py to config_utils.py")
    print("\nAll files under 2000 lines! ✨")

if __name__ == '__main__':
    split_config_utils_refined()
