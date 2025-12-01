"""Add extraction method selector to parcel_automation.py"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with "btn_frame = tk.Frame(all_tab"
insert_line = None
for i, line in enumerate(lines):
    if 'btn_frame = tk.Frame(all_tab, bg="white", padx=20, pady=20)' in line:
        insert_line = i
        break

if insert_line is None:
    print("ERROR: Could not find btn_frame line")
    exit(1)

# Insert extraction method selector before btn_frame
method_selector = [
    '        # Extraction method selector\n',
    '        method_frame = tk.Frame(all_tab, bg="white", padx=20, pady=10)\n',
    '        method_frame.pack(fill="x")\n',
    '        \n',
    '        tk.Label(\n',
    '            method_frame,\n',
    '            text="Extraction Method:",\n',
    '            font=("Segoe UI", 10, "bold"),\n',
    '            bg="white"\n',
    '        ).pack(anchor="w", pady=(0, 5))\n',
    '        \n',
    '        self.extraction_method = tk.StringVar(value="openai")\n',
    '        \n',
    '        tk.Radiobutton(\n',
    '            method_frame,\n',
    '            text="OpenAI Vision API (Batch of 20, highly accurate, waits for 20 images)",\n',
    '            variable=self.extraction_method,\n',
    '            value="openai",\n',
    '            font=("Segoe UI", 9),\n',
    '            bg="white"\n',
    '        ).pack(anchor="w", padx=20)\n',
    '        \n',
    '        tk.Radiobutton(\n',
    '            method_frame,\n',
    '            text="BeautifulSoup OCR (Individual, processes immediately)",\n',
    '            variable=self.extraction_method,\n',
    '            value="beautifulsoup",\n',
    '            font=("Segoe UI", 9),\n',
    '            bg="white"\n',
    '        ).pack(anchor="w", padx=20)\n',
    '        \n',
]

lines = lines[:insert_line] + method_selector + lines[insert_line:]

with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Added extraction method selector to Process All Addresses tab")
