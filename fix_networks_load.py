#!/usr/bin/env python3
"""
Fix Networks tab to load from queue_websites database table directly.
Fix Websites tab to load from google_places via API.
"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and replace the queue_websites API section with database loading
in_queue_websites_section = False
indent_level = 0
changes = 0

for i, line in enumerate(lines):
    # Find the queue_websites API section
    if "elif str(current_table).lower() == 'queue_websites':" in line:
        in_queue_websites_section = True
        indent_level = len(line) - len(line.lstrip())
        
        # Replace the entire section with database loading
        # Find the end of this elif block
        end_idx = i + 1
        while end_idx < len(lines):
            next_line = lines[end_idx]
            next_indent = len(next_line) - len(next_line.lstrip())
            
            # Check if we hit the next elif/else at the same level
            if next_indent <= indent_level and next_line.strip() and not next_line.strip().startswith('#'):
                if 'elif ' in next_line or next_line.strip().startswith('else:'):
                    break
            end_idx += 1
        
        # Replace this entire block
        replacement = f"{' ' * indent_level}elif str(current_table).lower() == 'queue_websites':\n"
        replacement += f"{' ' * (indent_level + 4)}# Networks tab: load from queue_websites database table directly\n"
        replacement += f"{' ' * (indent_level + 4)}try:\n"
        replacement += f"{' ' * (indent_level + 8)}if not silent:\n"
        replacement += f"{' ' * (indent_level + 12)}log_to_file(f\"[Networks] Loading from queue_websites table\")\n"
        replacement += f"{' ' * (indent_level + 8)}cursor = conn.cursor(dictionary=True)\n"
        replacement += f"{' ' * (indent_level + 8)}cursor.execute(\"SELECT * FROM queue_websites ORDER BY id ASC\")\n"
        replacement += f"{' ' * (indent_level + 8)}db_rows = cursor.fetchall()\n"
        replacement += f"{' ' * (indent_level + 8)}cursor.close()\n"
        replacement += f"{' ' * (indent_level + 8)}rows = []\n"
        replacement += f"{' ' * (indent_level + 8)}for row in db_rows:\n"
        replacement += f"{' ' * (indent_level + 12)}rows.append({{\n"
        replacement += f"{' ' * (indent_level + 16)}'id': row.get('id'),\n"
        replacement += f"{' ' * (indent_level + 16)}'link': row.get('link') or '',\n"
        replacement += f"{' ' * (indent_level + 16)}'name': row.get('name') or '',\n"
        replacement += f"{' ' * (indent_level + 16)}'run_interval_minutes': row.get('run_interval_minutes') or 0,\n"
        replacement += f"{' ' * (indent_level + 16)}'next_run': row.get('next_run'),\n"
        replacement += f"{' ' * (indent_level + 16)}'processed_at': row.get('processed_at'),\n"
        replacement += f"{' ' * (indent_level + 16)}'status': row.get('status') or 'queued',\n"
        replacement += f"{' ' * (indent_level + 16)}'error_message': row.get('error_message') or '',\n"
        replacement += f"{' ' * (indent_level + 16)}'steps': {{}}\n"
        replacement += f"{' ' * (indent_level + 12)}}})\n"
        replacement += f"{' ' * (indent_level + 8)}if not silent:\n"
        replacement += f"{' ' * (indent_level + 12)}log_to_file(f\"[Networks] Loaded {{len(rows)}} networks from queue_websites table\")\n"
        replacement += f"{' ' * (indent_level + 4)}except Exception as e:\n"
        replacement += f"{' ' * (indent_level + 8)}error_occurred = True\n"
        replacement += f"{' ' * (indent_level + 8)}error_msg = f\"Failed to load queue_websites: {{str(e)[:80]}}\"\n"
        replacement += f"{' ' * (indent_level + 8)}log_to_file(f\"[Networks] {{error_msg}}\")\n"
        replacement += f"{' ' * (indent_level + 8)}rows = []\n"
        
        # Remove old lines and insert new
        lines = lines[:i] + [replacement] + lines[end_idx:]
        changes += 1
        print(f"✓ Replaced queue_websites section with database loading (lines {i+1}-{end_idx})")
        break

# Now add a new section for Websites tab (google_places API)
# Find where to insert it (after queue_websites section)
for i, line in enumerate(lines):
    if "elif str(current_table).lower() == 'queue_websites':" in line:
        # Find the end of this block
        indent_level = len(line) - len(line.lstrip())
        end_idx = i + 1
        while end_idx < len(lines):
            next_line = lines[end_idx]
            next_indent = len(next_line) - len(next_line.lstrip())
            if next_indent <= indent_level and next_line.strip() and not next_line.strip().startswith('#'):
                if 'elif ' in next_line or next_line.strip().startswith('else:'):
                    break
            end_idx += 1
        
        # Insert Websites tab section
        websites_section = f"{' ' * indent_level}elif str(current_table).lower() in ('listing_websites', 'websites'):\n"
        websites_section += f"{' ' * (indent_level + 4)}# Websites tab: load from google_places where Website is not empty\n"
        websites_section += f"{' ' * (indent_level + 4)}try:\n"
        websites_section += f"{' ' * (indent_level + 8)}api_url = \"http://localhost/step5/get_websites.php?limit=200\"\n"
        websites_section += f"{' ' * (indent_level + 8)}if not silent:\n"
        websites_section += f"{' ' * (indent_level + 12)}log_to_file(f\"[Websites] Calling API: {{api_url}}\")\n"
        websites_section += f"{' ' * (indent_level + 8)}resp = requests.get(api_url, timeout=10)\n"
        websites_section += f"{' ' * (indent_level + 8)}if resp.status_code == 200:\n"
        websites_section += f"{' ' * (indent_level + 12)}data = resp.json()\n"
        websites_section += f"{' ' * (indent_level + 12)}if data.get('ok'):\n"
        websites_section += f"{' ' * (indent_level + 16)}gps = data.get('websites', [])\n"
        websites_section += f"{' ' * (indent_level + 16)}rows = []\n"
        websites_section += f"{' ' * (indent_level + 16)}for gp in gps:\n"
        websites_section += f"{' ' * (indent_level + 20)}rows.append({{\n"
        websites_section += f"{' ' * (indent_level + 24)}'id': gp.get('id'),\n"
        websites_section += f"{' ' * (indent_level + 24)}'link': gp.get('Website') or '',\n"
        websites_section += f"{' ' * (indent_level + 24)}'name': gp.get('Name') or '',\n"
        websites_section += f"{' ' * (indent_level + 24)}'run_interval_minutes': 0,\n"
        websites_section += f"{' ' * (indent_level + 24)}'next_run': None,\n"
        websites_section += f"{' ' * (indent_level + 24)}'processed_at': None,\n"
        websites_section += f"{' ' * (indent_level + 24)}'status': 'queued',\n"
        websites_section += f"{' ' * (indent_level + 24)}'steps': {{}}\n"
        websites_section += f"{' ' * (indent_level + 20)}}})\n"
        websites_section += f"{' ' * (indent_level + 16)}custom_source = 'websites'\n"
        websites_section += f"{' ' * (indent_level + 16)}if not silent:\n"
        websites_section += f"{' ' * (indent_level + 20)}log_to_file(f\"[Websites] Loaded {{len(rows)}} websites via API\")\n"
        websites_section += f"{' ' * (indent_level + 12)}else:\n"
        websites_section += f"{' ' * (indent_level + 16)}error_occurred = True\n"
        websites_section += f"{' ' * (indent_level + 16)}error_msg = f\"Websites API error: {{data.get('error', 'unknown')}}\"\n"
        websites_section += f"{' ' * (indent_level + 16)}log_to_file(f\"[Websites] {{error_msg}}\")\n"
        websites_section += f"{' ' * (indent_level + 16)}rows = []\n"
        websites_section += f"{' ' * (indent_level + 8)}else:\n"
        websites_section += f"{' ' * (indent_level + 12)}error_occurred = True\n"
        websites_section += f"{' ' * (indent_level + 12)}error_msg = f\"Websites API failed: HTTP {{resp.status_code}}\"\n"
        websites_section += f"{' ' * (indent_level + 12)}log_to_file(f\"[Websites] {{error_msg}}\")\n"
        websites_section += f"{' ' * (indent_level + 12)}rows = []\n"
        websites_section += f"{' ' * (indent_level + 4)}except Exception as e:\n"
        websites_section += f"{' ' * (indent_level + 8)}error_occurred = True\n"
        websites_section += f"{' ' * (indent_level + 8)}error_msg = f\"Websites load failed: {{str(e)[:80]}}\"\n"
        websites_section += f"{' ' * (indent_level + 8)}log_to_file(f\"[Websites] {{error_msg}}\")\n"
        websites_section += f"{' ' * (indent_level + 8)}rows = []\n"
        
        lines.insert(end_idx, websites_section)
        changes += 1
        print(f"✓ Added Websites tab section (google_places API)")
        break

# Also need to change the Websites tab button to point to "listing_websites"
for i, line in enumerate(lines):
    if 'tab_websites = make_tab_btn("Websites", "queue_websites")' in line:
        lines[i] = line.replace('"queue_websites"', '"listing_websites"')
        changes += 1
        print(f"✓ Changed Websites tab to load from listing_websites")
        break

# Save
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"\n✓ Made {changes} changes total")
print("✓ Networks tab now loads from queue_websites DATABASE TABLE")
print("✓ Websites tab now loads from google_places via API")
