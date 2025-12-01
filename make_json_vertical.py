"""
Change JSON display from horizontal table to vertical key-value display
"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the create_json_tab method to create a vertical display
old_json_tab = '''    def create_json_tab(self):
        """Create the JSON results tab"""
        json_tab = tk.Frame(self.notebook, bg="white")
        self.notebook.add(json_tab, text="JSON Results")

        # Create treeview for JSON data
        tree_frame = tk.Frame(json_tab, bg="white", padx=10, pady=10)
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL)
        h_scroll = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)

        # Create treeview
        columns = ("address", "parcel_number", "property_name", "jurisdiction", 
                   "taxpayer_name", "appraised_value", "lot_area", "levy_code",
                   "num_units", "num_buildings")
        
        self.json_tree = ttk.Treeview(
            tree_frame, columns=columns, show='headings',
            yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set
        )

        v_scroll.config(command=self.json_tree.yview)
        h_scroll.config(command=self.json_tree.xview)

        # Configure columns
        self.json_tree.heading("address", text="Address")
        self.json_tree.heading("parcel_number", text="Parcel #")
        self.json_tree.heading("property_name", text="Property Name")
        self.json_tree.heading("jurisdiction", text="Jurisdiction")
        self.json_tree.heading("taxpayer_name", text="Taxpayer Name")
        self.json_tree.heading("appraised_value", text="Appraised Value")
        self.json_tree.heading("lot_area", text="Lot Area")
        self.json_tree.heading("levy_code", text="Levy Code")
        self.json_tree.heading("num_units", text="# Units")
        self.json_tree.heading("num_buildings", text="# Buildings")

        for col in columns:
            self.json_tree.column(col, width=150, minwidth=100)

        self.json_tree.pack(fill=tk.BOTH, expand=True)'''

new_json_tab = '''    def create_json_tab(self):
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

        self.json_tree.pack(fill=tk.BOTH, expand=True)'''

content = content.replace(old_json_tab, new_json_tab)

# Replace update_json_display to populate vertical display
old_update = '''    def update_json_display(self, data):
        """Update the JSON treeview with new data"""
        # Extract fields
        fields = data.get('extracted_fields', {})

        values = (
            data.get('address', ''),
            fields.get('parcel_number', ''),
            fields.get('property_name', ''),
            fields.get('jurisdiction', ''),
            fields.get('taxpayer_name', ''),
            fields.get('appraised_value', ''),
            fields.get('lot_area', ''),
            fields.get('levy_code', ''),
            fields.get('num_units', ''),
            fields.get('num_buildings', '')
        )

        # Add to treeview
        self.json_tree.insert('', 'end', values=values)

        # Switch to JSON tab to show results
        self.notebook.select(1)  # Index 1 is JSON Results tab'''

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
        self.notebook.select(1)  # Index 1 is JSON Results tab'''

content = content.replace(old_update, new_update)

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Changed JSON display from horizontal table to vertical key-value format")
print("✓ Added warning highlighting for missing/null values")
print("✓ Shows 'Google Address ID' and all extracted fields")
