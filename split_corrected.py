#!/usr/bin/env python3
"""
Corrected split with proper class boundaries
"""

def corrected_split():
    with open('config_utils_backup.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    total_lines = len(lines)
    
    # Read imports
    imports_end = 0
    for i, line in enumerate(lines):
        if line.startswith(('import ', 'from ')) or line.strip().startswith('#'):
            imports_end = i + 1
        elif line.strip() and not line.strip().startswith('#'):
            break
    
    imports_block = ''.join(lines[:imports_end])
    
    # Corrected splits - proper boundaries:
    splits = [
        ('config_core.py', 0, 477, 'Core utilities and login (before SplashScreen class)'),
        ('config_splash.py', 477, 567, 'SplashScreen class'),
        ('config_hud_part1.py', 567, 2500, 'OldCompactHUD - Part 1'),
        ('config_hud_part2.py', 2500, 4500, 'OldCompactHUD - Part 2'),
        ('config_hud_part3.py', 4500, 6500, 'OldCompactHUD - Part 3'),
        ('config_hud_part4.py', 6500, 7283, 'OldCompactHUD - Part 4'),
        ('config_helpers.py', 7283, 7686, 'HUD helper functions'),
        ('config_address_match.py', 7686, 9622, 'Address Match window'),
        ('config_insert_db.py', 9622, total_lines, 'Insert DB window'),
    ]
    
    print("Creating corrected split files...")
    
    for filename, start, end, description in splits:
        line_count = end - start
        
        with open(filename, 'w', encoding='utf-8') as f:
            if start > 0:
                f.write(imports_block)
                f.write(f'\n# {description}\n\n')
                f.write('from config_core import *\n')
                
                if filename == 'config_hud_part1.py':
                    f.write('from config_splash import SplashScreen\n')
                
                f.write('\n')
            
            f.writelines(lines[start:end])
        
        print(f"✅ {filename:30s} {line_count:5d} lines")
    
    # Create main
    with open('config_utils.py', 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('"""Main entry point - imports all split modules"""\n\n')
        f.write('from config_core import *\n')
        f.write('from config_splash import *\n')
        f.write('from config_hud_part1 import *\n')
        f.write('from config_hud_part2 import *\n')
        f.write('from config_hud_part3 import *\n')
        f.write('from config_hud_part4 import *\n')
        f.write('from config_helpers import *\n')
        f.write('from config_address_match import *\n')
        f.write('from config_insert_db import *\n')
    
    print("\n✅ Split complete with corrected boundaries!")

if __name__ == '__main__':
    corrected_split()
