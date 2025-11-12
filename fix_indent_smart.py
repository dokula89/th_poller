#!/usr/bin/env python3
"""
Smart indentation fixer for config_utils.py
This script attempts to automatically detect and fix common indentation errors.
"""
import re
import sys

def fix_indentation(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    fixed_lines = []
    indent_stack = [0]  # Stack to track expected indentation levels
    prev_line_type = None  # 'block_start', 'block_end', 'normal'
    
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        
        # Skip empty lines and comments
        if not stripped or stripped.startswith('#'):
            fixed_lines.append(line)
            continue
        
        # Calculate current indentation
        current_indent = len(line) - len(line.lstrip())
        
        # Detect block-ending keywords
        if stripped.startswith(('except ', 'except:', 'finally:', 'elif ', 'else:')):
            # These should match the indentation of their corresponding try/if
            # Pop back to the parent block level
            if len(indent_stack) > 1:
                indent_stack.pop()
            expected_indent = indent_stack[-1]
            fixed_line = ' ' * expected_indent + stripped
            fixed_lines.append(fixed_line)
            # Push current level for the block's body
            indent_stack.append(expected_indent)
            prev_line_type = 'block_start'
            continue
        
        # Detect block-starting keywords
        if re.search(r'(if |elif |else:|for |while |try:|except |except:|finally:|def |class |with )', stripped):
            if stripped.endswith(':'):
                # This starts a new block
                expected_indent = indent_stack[-1] + (4 if prev_line_type == 'block_start' else 0)
                fixed_line = ' ' * expected_indent + stripped
                fixed_lines.append(fixed_line)
                # Push the new block level
                indent_stack.append(expected_indent + 4)
                prev_line_type = 'block_start'
                continue
        
        # Normal line - use current stack level
        expected_indent = indent_stack[-1] if prev_line_type == 'block_start' else indent_stack[-1]
        
        # Detect dedent (line should go back a level)
        if current_indent < indent_stack[-1] and len(indent_stack) > 1:
            # Pop until we find a matching level
            while len(indent_stack) > 1 and indent_stack[-1] > current_indent:
                indent_stack.pop()
        
        fixed_line = ' ' * indent_stack[-1] + stripped
        fixed_lines.append(fixed_line)
        prev_line_type = 'normal'
    
    # Write back
    with open(filename, 'w', encoding='utf-8') as f:
        f.writelines(fixed_lines)
    
    print(f"Fixed indentation in {filename}")

if __name__ == '__main__':
    fix_indentation('config_utils.py')
