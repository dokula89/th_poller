"""
Force replace the JSON tab creation with vertical display
"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the create_json_tab method (around line 264)
for i, line in enumerate(lines):
    if 'def create_json_tab(self):' in line:
        print(f"Found create_json_tab at line {i+1}")
        
        # Find the end of this method (next method definition)
        end_idx = i + 1
        for j in range(i + 1, min(i + 100, len(lines))):
            if lines[j].strip().startswith('def ') and not lines[j].strip().startswith('def create_json_tab'):
                end_idx = j
                print(f"Method ends at line {j+1}")
                break
        
        # Create the new vertical method
        new_method = '''    def create_json_tab(self):
        """Create the JSON results tab with vertical key-value display"""
        json_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(json_tab, text="JSON Results")

        # Create treeview for vertical key-value display
        tree_frame = tk.Frame(json_tab, bg="white", padx=10, pady=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbar
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        # Create treeview with 2 columns: Field and Value
        self.json_tree = ttk.Treeview(
            tree_frame, 
            columns=("field", "value"), 
            show='headings',
            yscrollcommand=v_scroll.set
        )

        v_scroll.config(command=self.json_tree.yview)

        # Configure columns
        self.json_tree.heading("field", text="Field")
        self.json_tree.heading("value", text="Value")
        
        self.json_tree.column("field", width=200, minwidth=150)
        self.json_tree.column("value", width=500, minwidth=300)

        self.json_tree.pack(fill=tk.BOTH, expand=True)

'''
        
        # Replace the method
        lines[i:end_idx] = [new_method]
        print(f"Replaced lines {i+1} to {end_idx}")
        break

# Now find and replace update_json_display
for i, line in enumerate(lines):
    if 'def update_json_display(self, data):' in line:
        print(f"Found update_json_display at line {i+1}")
        
        # Find the end of this method
        end_idx = i + 1
        for j in range(i + 1, min(i + 50, len(lines))):
            if lines[j].strip().startswith('def '):
                end_idx = j
                print(f"Method ends at line {j+1}")
                break
        
        # Create new update method
        new_update = '''    def update_json_display(self, data):
        """Update the JSON treeview with new data in vertical format"""
        # Clear previous data
        for item in self.json_tree.get_children():
            self.json_tree.delete(item)
        
        # Extract fields
        fields = data.get('extracted_fields', {})
        
        # Add separator
        self.json_tree.insert('', 'end', values=("=" * 40, "=" * 80))
        self.json_tree.insert('', 'end', values=("LATEST EXTRACTION", ""))
        self.json_tree.insert('', 'end', values=("=" * 40, "=" * 80))
        
        # Display data vertically
        field_mapping = [
            ("Google Address ID", data.get('id', 'N/A')),
            ("Address", data.get('address', 'N/A')),
            ("Parcel Number", fields.get('parcel_number', 'N/A')),
            ("Property Name", fields.get('property_name', 'N/A')),
            ("Jurisdiction", fields.get('jurisdiction', 'N/A')),
            ("Taxpayer Name", fields.get('taxpayer_name', 'N/A')),
            ("Address (Extracted)", fields.get('address', 'N/A')),
            ("Appraised Value", fields.get('appraised_value', 'N/A')),
            ("Lot Area (sq ft)", fields.get('lot_area', 'N/A')),
            ("Levy Code", fields.get('levy_code', 'N/A')),
            ("# of Units", fields.get('num_units', 'N/A')),
            ("# of Buildings", fields.get('num_buildings', 'N/A')),
        ]
        
        for field_name, field_value in field_mapping:
            # Highlight empty/null values
            if not field_value or field_value == 'N/A':
                self.json_tree.insert('', 'end', values=(field_name, "⚠ MISSING"), tags=('warning',))
            else:
                self.json_tree.insert('', 'end', values=(field_name, field_value))
        
        # Add tag styling for warnings
        self.json_tree.tag_configure('warning', foreground='red')
        
        # Switch to JSON tab to show results
        self.notebook.select(1)  # Index 1 is JSON Results tab

'''
        
        # Replace the method
        lines[i:end_idx] = [new_update]
        print(f"Replaced lines {i+1} to {end_idx}")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ FORCEFULLY replaced both methods with vertical display!")
