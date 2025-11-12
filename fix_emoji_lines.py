with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix line 1421 (index 1420)
lines[1420] = '                    def add_path_link(path, label="🏁"):\n'

# Also fix line 2665 which has corrupted characters
lines[2664] = '                                    status_win.after(0, lambda: set_status_summary(idx, f"🏁 New: {_new_c} • Price Δ: {_price_c} • Inactive: {_inactive_c} • Total: {_total}", "#2ECC71"))\n'

with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print('Fixed corrupted emoji!')
