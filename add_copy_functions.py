import re

# Read file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find position after "json_tab = ..." line
insert_pos = content.find('self.notebook.add(json_tab, text="JSON Results")')
if insert_pos == -1:
    print('ERROR: Could not find json_tab addition')
    exit(1)

# Move to end of that line
insert_pos = content.find('\n', insert_pos) + 1

# Prepare button frame code
button_code = '''
        # Button frame at top
        button_frame = tk.Frame(json_tab, bg="white", pady=5)
        button_frame.pack(fill=tk.X)

        # Copy buttons
        copy_all_btn = tk.Button(
            button_frame,
            text="Copy All",
            command=self.copy_all_json_data,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10
        )
        copy_all_btn.pack(side=tk.LEFT, padx=5)

        copy_selected_btn = tk.Button(
            button_frame,
            text="Copy Selected",
            command=self.copy_selected_json_data,
            bg="#2196F3",
            fg="white",
            font=("Arial", 10, "bold"),
            padx=10
        )
        copy_selected_btn.pack(side=tk.LEFT, padx=5)
'''

# Insert button code
content = content[:insert_pos] + button_code + content[insert_pos:]

# Now add copy methods after create_json_tab
method_pos = content.find('def create_process_all_tab(self):')
if method_pos == -1:
    print('ERROR: Could not find create_process_all_tab')
    exit(1)

copy_methods = '''
    def copy_all_json_data(self):
        """Copy all JSON data to clipboard"""
        try:
            items = self.json_tree.get_children()
            if not items:
                self.log_activity("No data to copy")
                return
            
            data = []
            for item in items:
                values = self.json_tree.item(item, 'values')
                data.append(f"{values[0]}: {values[1]}")
            
            text = '\n'.join(data)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log_activity(f"Copied {len(items)} fields to clipboard")
        except Exception as e:
            self.log_activity(f"ERROR copying data: {str(e)}")

    def copy_selected_json_data(self):
        """Copy selected JSON data to clipboard"""
        try:
            selected = self.json_tree.selection()
            if not selected:
                self.log_activity("No rows selected")
                return
            
            data = []
            for item in selected:
                values = self.json_tree.item(item, 'values')
                data.append(f"{values[0]}: {values[1]}")
            
            text = '\n'.join(data)
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.log_activity(f"Copied {len(selected)} fields to clipboard")
        except Exception as e:
            self.log_activity(f"ERROR copying selection: {str(e)}")

'''

# Insert copy methods
content = content[:method_pos] + copy_methods + content[method_pos:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(' Added copy buttons and methods')
