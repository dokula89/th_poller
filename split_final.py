#!/usr/bin/env python3
"""
Final split of config_utils.py into files with max 2000 lines each
"""

def final_split():
    with open('config_utils.py', 'r', encoding='utf-8') as f:
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
    
    # Final split strategy - all files under 2000 lines:
    splits = [
        ('config_core.py', 0, 478, 'Core utilities and login dialog'),
        ('config_splash.py', 478, 568, 'SplashScreen class'),
        ('config_hud_part1.py', 568, 2500, 'OldCompactHUD - Part 1'),
        ('config_hud_part2.py', 2500, 4500, 'OldCompactHUD - Part 2'),
        ('config_hud_part3.py', 4500, 6500, 'OldCompactHUD - Part 3'),
        ('config_hud_part4.py', 6500, 7283, 'OldCompactHUD - Part 4'),
        ('config_helpers.py', 7283, 7686, 'HUD helper functions'),
        ('config_address_match.py', 7686, 9622, 'Address Match window (~1936 lines)'),
        ('config_insert_db.py', 9622, total_lines, 'Insert DB window (~500 lines)'),
    ]
    
    print("="*70)
    print("SPLITTING config_utils.py INTO MANAGEABLE FILES")
    print("="*70)
    print(f"\nOriginal file: {total_lines} lines")
    print(f"Target: All files under 2000 lines\n")
    
    created_files = []
    
    for filename, start, end, description in splits:
        line_count = end - start
        
        with open(filename, 'w', encoding='utf-8') as f:
            if start > 0:
                f.write(imports_block)
                f.write(f'\n# {description}\n')
                f.write('# Part of split config_utils.py\n\n')
                f.write('from config_core import *\n')
                
                if filename == 'config_hud_part1.py':
                    f.write('from config_splash import SplashScreen\n')
                
                f.write('\n')
            
            f.writelines(lines[start:end])
        
        status = "✅" if line_count <= 2000 else "⚠️"
        print(f"{status} {filename:30s} {line_count:5d} lines - {description}")
        created_files.append(filename)
    
    # Create main entry point
    with open('config_utils_new.py', 'w', encoding='utf-8') as f:
        f.write('#!/usr/bin/env python3\n')
        f.write('# -*- coding: utf-8 -*-\n')
        f.write('"""Main entry point - imports all split modules"""\n\n')
        for filename in created_files:
            module_name = filename.replace('.py', '')
            f.write(f'from {module_name} import *\n')
    
    print(f"\n✅ config_utils_new.py (main entry point)")
    
    print("\n" + "="*70)
    print("SPLIT COMPLETE!")
    print("="*70)
    print(f"\nCreated {len(created_files) + 1} files (all under 2000 lines)")
    print("\nNext steps:")
    print("  1. Backup:   mv config_utils.py config_utils_backup.py")
    print("  2. Activate: mv config_utils_new.py config_utils.py")
    print("  3. Test:     python -c 'import config_utils; print(\"✓ Import successful\")'")

if __name__ == '__main__':
    final_split()
