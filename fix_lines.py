with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 849 (index 848)
lines[848] = '        DEFAULT_LABELS = ["ID", "Link", "Int", "Last", "Next", "Status", "Δ$", "+", "-", "Total", "✏️", "", ""]\n'

# Fix line 888 (index 887) 
lines[886] = '                    # Networks table: ID, Link, Int, Last, Next, Status, Δ$, +, -, Total, ✏️\n'
lines[887] = '                    labels = ["ID", "Link", "Int", "Last", "Next", "Status", "Δ$", "+", "-", "Total", "✏️", "", ""]\n'

# Fix line 970 (index 969)
lines[969] = '                # Columns: ID, Link, Int, Last, Next, Status, Δ$, +, -, ✏️, hidden1, hidden2\n'

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed all corrupted lines!')
