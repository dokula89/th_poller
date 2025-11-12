#!/usr/bin/env python3
"""
Add stats INSERT to Step 5 completion
"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with the stats summary in Step 5
for i, line in enumerate(lines):
    if 'job_stats[\'price_changes\'] = int(_price_c or 0)' in line:
        # Add INSERT statement after the stats are set, before finish_step
        # Find the finish_step call
        for j in range(i, min(i+10, len(lines))):
            if 'finish_step(idx, auto_continue)' in lines[j]:
                # Insert the stats INSERT code before finish_step
                indent = ' ' * 36  # Match indentation
                
                insert_code = [
                    f'{indent}# Insert stats into network_daily_stats\n',
                    f'{indent}try:\n',
                    f'{indent}    cursor.execute(\n',
                    f'{indent}        "INSERT INTO network_daily_stats (source_id, date, price_changes, apartments_added, apartments_subtracted, total_listings) "\n',
                    f'{indent}        "VALUES (%s, CURDATE(), %s, %s, %s, %s) "\n',
                    f'{indent}        "ON DUPLICATE KEY UPDATE price_changes=%s, apartments_added=%s, apartments_subtracted=%s, total_listings=%s",\n',
                    f'{indent}        (job_data.get("network_id"), _price_c, _new_c, _inactive_c, _total, _price_c, _new_c, _inactive_c, _total)\n',
                    f'{indent}    )\n',
                    f'{indent}    conn.commit()\n',
                    f'{indent}except Exception as stats_err:\n',
                    f'{indent}    status_win.after(0, lambda: log_activity(f"⚠️ Stats insert failed: {{stats_err}}", "#ffaa00"))\n',
                ]
                
                lines = lines[:j] + insert_code + lines[j:]
                print(f"✓ Added stats INSERT at line {j}")
                break
        break

# Save
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Stats tracking added to Step 5")
