#!/usr/bin/env python3
"""
Update Networks table to show stats columns instead of steps
"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the cols definition to include stats columns
old_cols = 'cols = ("ID", "Link", "Interval", "Next Run", "Last Run", "1.HTML", "2.JSON", "3.Extract", "4.Upload", "5.Insert DB", "6.Address Match", "Edit")'
new_cols = 'cols = ("ID", "Link", "Int", "Last", "Next", "Status", "Δ$", "+", "-", "Total", "✏️", "hidden1", "hidden2")'

if old_cols in content:
    content = content.replace(old_cols, new_cols)
    print("✓ Updated column definitions")
else:
    print("⚠ Column definition not found or already updated")

# Update DEFAULT_LABELS
old_default = 'DEFAULT_LABELS = ["ID", "Link", "Interval", "Next Run", "Last Run", "1.HTML", "2.JSON", "3.Extract", "4.Upload", "5.Insert DB", "6.Address Match", "Edit"]'
new_default = 'DEFAULT_LABELS = ["ID", "Link", "Int", "Last", "Next", "Status", "Δ$", "+", "-", "Total", "✏️", "", ""]'

if old_default in content:
    content = content.replace(old_default, new_default)
    print("✓ Updated DEFAULT_LABELS")
else:
    print("⚠ DEFAULT_LABELS not found or already updated")

# Update DEFAULT_WIDTHS to match new columns
old_widths = 'DEFAULT_WIDTHS = [60, 200, 60, 140, 140, 84, 84, 84, 90, 96, 120, 56]'
new_widths = 'DEFAULT_WIDTHS = [40, 250, 50, 70, 70, 50, 40, 35, 35, 50, 30, 0, 0]'

if old_widths in content:
    content = content.replace(old_widths, new_widths)
    print("✓ Updated DEFAULT_WIDTHS")
else:
    print("⚠ DEFAULT_WIDTHS not found or already updated")

# Update the Networks table configuration to show stats columns
# Find and replace the networks configuration section
networks_config_old = '''elif t in ("listing_networks", "queue_networks", "networks"):
                    labels[1] = "Link"
                    labels[2] = "CSS"
                    # Replace Next Run with a Summary column to show live stats
                    labels[3] = "Summary"
                    labels[4] = "Last Run"
                    widths[1] = 260
                    widths[2] = 160
                    # Make Summary wider to fit compact metrics
                    widths[3] = 420
                    widths[4] = 140
                    # Hide step columns for Networks table (1.HTML .. 6.Address Match)
                    try:
                        for idx in (5, 6, 7, 8, 9, 10):
                            widths[idx] = 0
                            labels[idx] = ""
                    except Exception:
                        pass'''

networks_config_new = '''elif t in ("listing_networks", "queue_networks", "networks"):
                    # Networks table: ID, Link, Int, Last, Next, Status, Δ$, +, -, Total, ✏️
                    labels = ["ID", "Link", "Int", "Last", "Next", "Status", "Δ$", "+", "-", "Total", "✏️", "", ""]
                    widths = [40, 250, 50, 70, 70, 50, 40, 35, 35, 50, 30, 0, 0]'''

if networks_config_old in content:
    content = content.replace(networks_config_old, networks_config_new)
    print("✓ Updated Networks table configuration")
else:
    print("⚠ Networks configuration not found or already updated")

# Save
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ Networks table columns updated to show stats!")
print("  Columns: ID, Link, Int, Last, Next, Status, Δ$, +, -, Total, ✏️")
