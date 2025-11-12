#!/usr/bin/env python3
"""
Add tooltip display and click-to-copy event handlers
"""

with open('config_hud.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find where the tree is created and add event bindings
tree_line = None
for i, line in enumerate(lines):
        if 'self._queue_tree = ttk.Treeview' in line:
            tree_line = i
            break

if tree_line:
    # Find the end of the tree setup (look for next major section)
    insert_at = tree_line + 1
    for j in range(tree_line + 1, min(tree_line + 200, len(lines))):
        # Find a good place after column setup
        if 'self._local_step_overrides' in lines[j]:
            insert_at = j + 1
            break
    
    # Add motion handler for tooltips
    tooltip_code = [
        '\n',
        '        # Event bindings for tooltips and click-to-copy\n',
        '        def _on_tree_motion(event):\n',
        '            """Show tooltip for error messages"""\n',
        '            try:\n',
        '                item = self._queue_tree.identify_row(event.y)\n',
        '                column = self._queue_tree.identify_column(event.x)\n',
        '                \n',
        '                if item and column:\n',
        '                    tooltip_key = f"{item}|{column}"\n',
        '                    if tooltip_key in self._cell_tooltips:\n',
        '                        # Show tooltip\n',
        '                        _hide_tooltip()\n',
        '                        msg = self._cell_tooltips[tooltip_key]\n',
        '                        \n',
        '                        # Create tooltip window\n',
        '                        tip = tk.Toplevel()\n',
        '                        tip.wm_overrideredirect(True)\n',
        '                        x = event.x_root + 10\n',
        '                        y = event.y_root + 10\n',
        '                        tip.wm_geometry(f"+{x}+{y}")\n',
        '                        \n',
        '                        label = tk.Label(tip, text=msg, background="#ffffe0",\n',
        '                                       relief="solid", borderwidth=1,\n',
        '                                       font=("Segoe UI", 9))\n',
        '                        label.pack()\n',
        '                        self._active_tooltip = tip\n',
        '                    else:\n',
        '                        _hide_tooltip()\n',
        '                else:\n',
        '                    _hide_tooltip()\n',
        '            except Exception:\n',
        '                pass\n',
        '        \n',
        '        def _on_tree_click(event):\n',
        '            """Copy error message to clipboard on click"""\n',
        '            try:\n',
        '                item = self._queue_tree.identify_row(event.y)\n',
        '                column = self._queue_tree.identify_column(event.x)\n',
        '                \n',
        '                # Get column index (Status is usually column 5 or 6)\n',
        '                if item and column:\n',
        '                    tooltip_key = f"{item}|{column}"\n',
        '                    if tooltip_key in self._cell_tooltips:\n',
        '                        msg = self._cell_tooltips[tooltip_key]\n',
        '                        self._root.clipboard_clear()\n',
        '                        self._root.clipboard_append(msg)\n',
        '                        print(f"Copied to clipboard: {msg[:50]}...")\n',
        '            except Exception as e:\n',
        '                print(f"Click error: {e}")\n',
        '        \n',
        '        self._queue_tree.bind("<Motion>", _on_tree_motion)\n',
        '        self._queue_tree.bind("<Button-1>", _on_tree_click)\n',
        '        self._queue_tree.bind("<Leave>", lambda e: _hide_tooltip())\n',
        '\n',
    ]
    
    lines = lines[:insert_at] + tooltip_code + lines[insert_at:]
    print(f"✓ Added tooltip and click handlers at line {insert_at}")
else:
    print("✗ Could not find tree creation")

# Save
with open('config_hud.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Event handlers added successfully")
