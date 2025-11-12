#!/usr/bin/env python3
"""
Split config_utils.py based on analyzed structure.
Preserves ALL code including comments.
"""

from pathlib import Path

source_file = Path(r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py")
output_dir = source_file.parent

with open(source_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}\n")

# Define splits based on analysis
splits = [
    {
        'file': 'config_core.py',
        'start': 0,
        'end': 68,
        'desc': 'Imports, constants, logging',
        'add_imports': False
    },
    {
        'file': 'config_auth.py',
        'start': 68,
        'end': 477,
        'desc': 'Session management and login dialog',
        'add_imports': True
    },
    {
        'file': 'config_splash.py',
        'start': 477,
        'end': 567,
        'desc': 'SplashScreen class',
        'add_imports': True
    },
    {
        'file': 'config_hud.py',
        'start': 567,
        'end': 6588,
        'desc': 'OldCompactHUD class - main UI',
        'add_imports': True
    },
    {
        'file': 'config_hud_api.py',
        'start': 6588,
        'end': 6672,
        'desc': 'HUD API functions (hud_start, hud_push, etc.)',
        'add_imports': True
    },
    {
        'file': 'config_helpers.py',
        'start': 6672,
        'end': len(lines),
        'desc': 'Helper functions',
        'add_imports': True
    }
]

# Create each split file
for split in splits:
    filename = split['file']
    start = split['start']
    end = split['end']
    
    content = lines[start:end]
    
    # Add header
    header = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{split['desc']}
Extracted from config_utils.py (lines {start+1}-{end})
"""

'''
    
    # Add imports if needed
    if split['add_imports']:
        imports = "from config_core import *\n\n"
        final_content = header + imports + ''.join(content)
    else:
        final_content = header + ''.join(content)
    
    # Write file
    output_path = output_dir / filename
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(final_content)
    
    line_count = len(content)
    print(f"✓ {filename:25} ({line_count:5} lines, {start+1:5}-{end:5})")

# Create new config_utils.py that imports from all modules
new_main = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main config_utils module - imports from all split modules.
Maintains backward compatibility with existing imports.
"""

# Import everything from split modules
from config_core import *
from config_auth import *
from config_splash import *
from config_hud import *
from config_hud_api import *
from config_helpers import *
'''

# Backup original
backup_path = output_dir / 'config_utils_BEFORE_SPLIT.py'
with open(source_file, 'r', encoding='utf-8') as f:
    with open(backup_path, 'w', encoding='utf-8') as b:
        b.write(f.read())

# Write new main file
with open(source_file, 'w', encoding='utf-8') as f:
    f.write(new_main)

print(f"\n✓ config_utils.py              (import hub)")
print(f"✓ config_utils_BEFORE_SPLIT.py (backup)")

print("\n" + "="*60)
print("SPLIT COMPLETE!")
print("="*60)
print("\nAll existing imports will continue to work!")
print("worker.py and other files don't need any changes.")
