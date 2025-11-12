#!/usr/bin/env python3
"""
Change Networks tab to load from queue_websites instead of listing_networks
"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# Change the default table from listing_networks to queue_websites
old_default = 'self._current_table = tk.StringVar(value="listing_networks")'
new_default = 'self._current_table = tk.StringVar(value="queue_websites")'
if old_default in content:
    content = content.replace(old_default, new_default)
    print("✓ Changed default table to queue_websites")
    changes += 1

# Change the Networks tab button to load queue_websites
old_tab = 'tab_networks = make_tab_btn("Networks", "listing_networks")'
new_tab = 'tab_networks = make_tab_btn("Networks", "queue_websites")'
if old_tab in content:
    content = content.replace(old_tab, new_tab)
    print("✓ Changed Networks tab to load queue_websites")
    changes += 1

# Update the column configuration to recognize queue_websites as networks table
old_config = 'elif t in ("listing_networks", "queue_networks", "networks"):'
new_config = 'elif t in ("queue_websites", "listing_websites", "websites"):'
if old_config in content:
    content = content.replace(old_config, new_config)
    print("✓ Updated column config to use queue_websites")
    changes += 1

# Update the tab status dictionary key
old_status = '"listing_networks": "queued",'
new_status = '"queue_websites": "queued",'
if old_status in content and '"queue_websites": "queued",' not in content:
    content = content.replace(old_status, new_status)
    print("✓ Updated tab status key")
    changes += 1

# Update any references in conditional checks
content = content.replace(
    'if tbl_now not in (\'listing_networks\', \'queue_networks\', \'networks\'):',
    'if tbl_now not in (\'queue_websites\', \'listing_websites\', \'websites\'):'
)
content = content.replace(
    'if str(current_table).lower() in ("listing_networks", "queue_networks", "networks"):',
    'if str(current_table).lower() in ("queue_websites", "listing_websites", "websites"):'
)
print("✓ Updated conditional checks")
changes += 1

# Save
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✓ Made {changes} changes")
print("Networks tab now loads from queue_websites table")
