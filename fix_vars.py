#!/usr/bin/env python3
"""
Fix indentation by reindenting from specific line ranges.
This targets the known problematic areas.
"""
import re

def fix_specific_blocks():
    with open('config_utils.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Fix known problem areas by analyzing context
    # Lines 3906-4050: the parcel block that's badly indented
    
    # Strategy: Find and fix major structural issues
    fixed = []
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Check for metro_filter references that should be selected_metro
        line = line.replace('metro_filter', 'selected_metro')
        
        # Check for table references that should be current_table  
        if 'str(table).lower()' in line and 'str(current_table).lower()' not in line:
            line = line.replace('str(table).lower()', 'str(current_table).lower()')
        
        # Check for custom_source that needs to be in scope
        # (This is trickier - would need more context)
        
        fixed.append(line)
        i += 1
    
    # Write back
    with open('config_utils.py', 'w', encoding='utf-8') as f:
        f.writelines(fixed)
    
    print("Fixed variable references")

if __name__ == '__main__':
    fix_specific_blocks()
