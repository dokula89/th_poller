#!/usr/bin/env python3
"""Add copy buttons to JSON results tab"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with self.json_tree.pack and add buttons before it
for i, line in enumerate(lines):
    if 'self.json_tree.pack(fill=tk.BOTH, expand=True)' in line and i > 260 and i < 300:
        print(f"Found json_tree.pack at line {i+1}")
        
        # Add button frame and copy functionality before the pack
        new_lines = [
            "\n",
            "        # Button frame for copy operations\n",
            "        button_frame = tk.Frame(tree_frame, bg=\"white\")\n",
            "        button_frame.pack(fill=tk.X, pady=(0, 10))\n",
            "\n",
            "        copy_all_btn = tk.Button(\n",
            "            button_frame,\n",
            "            text=\"📋 Copy All\",\n",
            "            command=self.copy_all_json_data,\n",
            "            bg=\"#4CAF50\",\n",
            "            fg=\"white\",\n",
            "            font=('Arial', 10, 'bold'),\n",
            "            padx=20,\n",
            "            pady=5\n",
            "        )\n",
            "        copy_all_btn.pack(side=tk.LEFT, padx=5)\n",
            "\n",
            "        copy_selected_btn = tk.Button(\n",
            "            button_frame,\n",
            "            text=\"📄 Copy Selected\",\n",
            "            command=self.copy_selected_json_data,\n",
            "            bg=\"#2196F3\",\n",
            "            fg=\"white\",\n",
            "            font=('Arial', 10, 'bold'),\n",
            "            padx=20,\n",
            "            pady=5\n",
            "        )\n",
            "        copy_selected_btn.pack(side=tk.LEFT, padx=5)\n",
            "\n",
        ]
        
        # Insert before the pack line
        lines = lines[:i] + new_lines + [lines[i]]
        
        # Now add the copy methods after the create_json_tab method
        # Find the end of create_json_tab
        for j in range(i + len(new_lines) + 1, i + len(new_lines) + 10):
            if j < len(lines) and 'def create_process_all_tab' in lines[j]:
                # Insert the copy methods before this next method
                copy_methods = [
                    "\n",
                    "    def copy_all_json_data(self):\n",
                    "        \"\"\"Copy all JSON data to clipboard\"\"\"\n",
                    "        try:\n",
                    "            items = self.json_tree.get_children()\n",
                    "            text_data = []\n",
                    "            for item in items:\n",
                    "                values = self.json_tree.item(item)['values']\n",
                    "                text_data.append(f\"{values[0]}: {values[1]}\")\n",
                    "            \n",
                    "            clipboard_text = \"\\n\".join(text_data)\n",
                    "            self.window.clipboard_clear()\n",
                    "            self.window.clipboard_append(clipboard_text)\n",
                    "            self.append_log(\"✓ Copied all JSON data to clipboard\")\n",
                    "        except Exception as e:\n",
                    "            self.append_log(f\"✗ Error copying: {e}\")\n",
                    "\n",
                    "    def copy_selected_json_data(self):\n",
                    "        \"\"\"Copy selected JSON rows to clipboard\"\"\"\n",
                    "        try:\n",
                    "            selected = self.json_tree.selection()\n",
                    "            if not selected:\n",
                    "                self.append_log(\"⚠ No rows selected\")\n",
                    "                return\n",
                    "            \n",
                    "            text_data = []\n",
                    "            for item in selected:\n",
                    "                values = self.json_tree.item(item)['values']\n",
                    "                text_data.append(f\"{values[0]}: {values[1]}\")\n",
                    "            \n",
                    "            clipboard_text = \"\\n\".join(text_data)\n",
                    "            self.window.clipboard_clear()\n",
                    "            self.window.clipboard_append(clipboard_text)\n",
                    "            self.append_log(f\"✓ Copied {len(selected)} row(s) to clipboard\")\n",
                    "        except Exception as e:\n",
                    "            self.append_log(f\"✗ Error copying: {e}\")\n",
                    "\n",
                ]
                
                lines = lines[:j] + copy_methods + lines[j:]
                print(f"✓ Added copy methods before line {j+1}")
                break
        
        print(f"✓ Added copy buttons at line {i+1}")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Added copy functionality to JSON Results tab!")
print("  - 📋 Copy All button")
print("  - 📄 Copy Selected button")
print("  - Click rows to select them, then click Copy Selected")
