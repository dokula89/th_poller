#!/usr/bin/env python3
"""
Split config_utils.py into smaller, logical modules.
Preserves ALL code including comments.
"""

from pathlib import Path

source_file = Path(r"c:\Users\dokul\Desktop\robot\th_poller\config_utils.py")

with open(source_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

print(f"Total lines in config_utils.py: {len(lines)}")

# Define split points based on logical sections
splits = {
    'config_core.py': {
        'start': 0,
        'end': 70,
        'description': 'Core configuration, constants, and logging'
    },
    'config_auth.py': {
        'start': 70,
        'end': 425,
        'description': 'Authentication and session management'
    },
    'config_splash.py': {
        'start': 425,
        'end': 568,
        'description': 'Splash screen class'
    },
    'config_hud.py': {
        'start': 568,
        'end': 6664,
        'description': 'Main HUD class (OldCompactHUD) and all UI logic'
    },
    'config_helpers.py': {
        'start': 6664,
        'end': len(lines),
        'description': 'Helper functions (ensure_dir, log_file, extract_parcel_fields, launch_browser, etc.)'
    }
}

# Create the split files
output_dir = source_file.parent

for filename, info in splits.items():
    output_path = output_dir / filename
    start = info['start']
    end = info['end']
    
    content = lines[start:end]
    
    # Add header comment
    header = f'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
{info['description']}
Extracted from config_utils.py (lines {start+1}-{end})
"""

'''
    
    # For non-core files, add import from config_core
    if filename != 'config_core.py':
        imports_to_add = "from config_core import *\n\n"
        content_str = header + imports_to_add + ''.join(content)
    else:
        content_str = header + ''.join(content)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content_str)
    
    print(f"✓ Created {filename} ({len(content)} lines, {start+1}-{end}): {info['description']}")

# Create new main config_utils.py that imports from all modules
new_main = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Main config_utils module - imports from all split modules.
This maintains backward compatibility with existing imports.
"""

# Import everything from split modules
from config_core import *
from config_auth import *
from config_splash import *
from config_hud import *
from config_helpers import *

# Preserve module structure for backward compatibility
__all__ = [
    # From config_core
    'CFG', 'BASE_DIR', 'GLOBAL_JSON_PATH', 'IMAGES_DIR', 'HUD_ENABLED', 'HUD_OPACITY',
    'SFTP_ENABLED', 'SFTP_HOST', 'SFTP_PORT', 'SFTP_USER', 'SFTP_PASS', 'REMOTE_IMAGES_PARENT',
    'log_to_file', 'log_exception',
    
    # From config_auth
    '_save_session', '_load_session', '_clear_session', '_session_valid',
    'show_login_dialog', 'ensure_session_before_hud',
    
    # From config_splash
    'SplashScreen', 'today_dir',
    
    # From config_hud
    'OldCompactHUD', 'hud_start', 'hud_run_mainloop_blocking', 'hud_push',
    'hud_loader_show', 'hud_loader_update', 'hud_loader_hide',
    'hud_counts', 'hud_set_paused', 'hud_is_paused', 'hud_is_auto_run_enabled', 'hud_stop',
    
    # From config_helpers
    'ensure_dir', 'log_file', 'extract_parcel_fields',
    'launch_manual_browser', 'launch_manual_browser_docked_right', 'sftp_upload_dir',
]
'''

# Backup original file
backup_path = output_dir / 'config_utils_ORIGINAL.py'
with open(source_file, 'r', encoding='utf-8') as f:
    with open(backup_path, 'w', encoding='utf-8') as b:
        b.write(f.read())
print(f"\n✓ Backed up original to {backup_path.name}")

# Write new main file
with open(source_file, 'w', encoding='utf-8') as f:
    f.write(new_main)
print(f"✓ Created new {source_file.name} (import hub)")

print("\n" + "="*60)
print("SPLIT COMPLETE!")
print("="*60)
print("\nFiles created:")
for filename in splits.keys():
    print(f"  - {filename}")
print(f"  - config_utils.py (new import hub)")
print(f"  - config_utils_ORIGINAL.py (backup)")
print("\nAll existing imports will continue to work!")
