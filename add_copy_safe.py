"""Safely add copy buttons and methods to parcel_automation.py"""

# Read file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line "self.notebook.add(json_tab, text="JSON Results")"
insert_line = None
for i, line in enumerate(lines):
    if 'self.notebook.add(json_tab, text="JSON Results")' in line:
        insert_line = i + 1
        break

if insert_line is None:
    print("ERROR: Could not find json_tab addition line")
    exit(1)

# Insert button frame code after json_tab addition
button_lines = [
    '\n',
    '        # Button frame at top\n',
    '        button_frame = tk.Frame(json_tab, bg="white", pady=5)\n',
    '        button_frame.pack(fill=tk.X)\n',
    '\n',
    '        # Copy buttons\n',
    '        copy_all_btn = tk.Button(\n',
    '            button_frame,\n',
    '            text="Copy All",\n',
    '            command=self.copy_all_json_data,\n',
    '            bg="#4CAF50",\n',
    '            fg="white",\n',
    '            font=("Arial", 10, "bold"),\n',
    '            padx=10\n',
    '        )\n',
    '        copy_all_btn.pack(side=tk.LEFT, padx=5)\n',
    '\n',
    '        copy_selected_btn = tk.Button(\n',
    '            button_frame,\n',
    '            text="Copy Selected",\n',
    '            command=self.copy_selected_json_data,\n',
    '            bg="#2196F3",\n',
    '            fg="white",\n',
    '            font=("Arial", 10, "bold"),\n',
    '            padx=10\n',
    '        )\n',
    '        copy_selected_btn.pack(side=tk.LEFT, padx=5)\n',
]

lines = lines[:insert_line] + button_lines + lines[insert_line:]

# Find create_process_all_tab method
method_line = None
for i, line in enumerate(lines):
    if 'def create_process_all_tab(self):' in line:
        method_line = i
        break

if method_line is None:
    print("ERROR: Could not find create_process_all_tab")
    exit(1)

# Insert copy methods before create_process_all_tab
copy_method_lines = [
    '\n',
    '    def copy_all_json_data(self):\n',
    '        """Copy all JSON data to clipboard"""\n',
    '        try:\n',
    '            items = self.json_tree.get_children()\n',
    '            if not items:\n',
    '                self.log_activity("No data to copy")\n',
    '                return\n',
    '            \n',
    '            data = []\n',
    '            for item in items:\n',
    '                values = self.json_tree.item(item, "values")\n',
    '                data.append(f"{values[0]}: {values[1]}")\n',
    '            \n',
    '            text = "\\n".join(data)\n',
    '            self.root.clipboard_clear()\n',
    '            self.root.clipboard_append(text)\n',
    '            self.log_activity(f"Copied {len(items)} fields to clipboard")\n',
    '        except Exception as e:\n',
    '            self.log_activity(f"ERROR copying data: {str(e)}")\n',
    '\n',
    '    def copy_selected_json_data(self):\n',
    '        """Copy selected JSON data to clipboard"""\n',
    '        try:\n',
    '            selected = self.json_tree.selection()\n',
    '            if not selected:\n',
    '                self.log_activity("No rows selected")\n',
    '                return\n',
    '            \n',
    '            data = []\n',
    '            for item in selected:\n',
    '                values = self.json_tree.item(item, "values")\n',
    '                data.append(f"{values[0]}: {values[1]}")\n',
    '            \n',
    '            text = "\\n".join(data)\n',
    '            self.root.clipboard_clear()\n',
    '            self.root.clipboard_append(text)\n',
    '            self.log_activity(f"Copied {len(selected)} fields to clipboard")\n',
    '        except Exception as e:\n',
    '            self.log_activity(f"ERROR copying selection: {str(e)}")\n',
    '\n',
]

lines = lines[:method_line] + copy_method_lines + lines[method_line:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Added copy buttons and methods successfully")
