#!/usr/bin/env python3
"""
Fix Networks tab to load from 'networks' database table (not API, not queue_websites)
"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

changes = 0

# 1. Change Networks tab to load from 'networks' table
old_networks_tab = 'tab_networks = make_tab_btn("Networks", "queue_websites")'
new_networks_tab = 'tab_networks = make_tab_btn("Networks", "networks")'
if old_networks_tab in content:
    content = content.replace(old_networks_tab, new_networks_tab)
    print("✓ Changed Networks tab to load from 'networks' table")
    changes += 1

# 2. Change default table to 'networks'
old_default = 'self._current_table = tk.StringVar(value="queue_websites")'
new_default = 'self._current_table = tk.StringVar(value="networks")'
if old_default in content:
    content = content.replace(old_default, new_default)
    print("✓ Changed default table to 'networks'")
    changes += 1

# 3. Add 'networks' to tab_status dictionary (if not already there)
if '"networks": "queued",' not in content:
    # Find the tab_status section and add networks
    old_status = '            "listing_networks": "queued",'
    new_status = '            "networks": "queued",'
    if old_status in content:
        content = content.replace(old_status, new_status)
        print("✓ Updated tab_status to use 'networks'")
        changes += 1

# 4. Update the column configuration to recognize 'networks' table
old_col_check = 'elif t in ("queue_websites", "listing_websites", "websites"):'
new_col_check = 'elif t in ("networks", "listing_networks", "queue_networks"):'
if old_col_check in content:
    content = content.replace(old_col_check, new_col_check)
    print("✓ Updated column config for 'networks' table")
    changes += 1

# 5. Update conditional checks
old_conditional = "if tbl_now not in ('queue_websites', 'listing_websites', 'websites'):"
new_conditional = "if tbl_now not in ('networks', 'listing_networks', 'queue_networks'):"
if old_conditional in content:
    content = content.replace(old_conditional, new_conditional)
    print("✓ Updated conditional checks")
    changes += 1

# 6. Remove the special API handling for queue_websites in _refresh_queue_table
# This will force it to use default database loading
old_api_section = """            elif str(current_table).lower() == 'queue_websites':
                # Special handling for Websites tab: call API to list google_places with non-empty Website
                try:
                    api_url = "http://localhost/step5/get_websites.php?limit=200"
                    if not silent:
                        log_to_file(f"[Websites] Calling API: {api_url}")
                    resp = requests.get(api_url, timeout=10)"""

new_api_section = """            elif str(current_table).lower() == 'websites_disabled':
                # DISABLED: Special handling for Websites tab
                try:
                    api_url = "http://localhost/step5/get_websites.php?limit=200"
                    if not silent:
                        log_to_file(f"[Websites] Calling API: {api_url}")
                    resp = requests.get(api_url, timeout=10)"""

if old_api_section in content:
    content = content.replace(old_api_section, new_api_section)
    print("✓ Disabled API loading - will use database instead")
    changes += 1

# Save
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"\n✓ Made {changes} changes")
print("Networks tab will now load from 'networks' database table")
print("No API calls - direct database query")
