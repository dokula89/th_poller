#!/usr/bin/env python3
"""Re-apply all the improvements from today's session"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

changes_made = []

# 1. Find and update OCR upscaling to 6x
for i, line in enumerate(lines):
    if 'scale_factor = 4' in line and '880x560' in line:
        lines[i] = '            scale_factor = 6  # 6x upscale: 220x140 -> 1320x840\n'
        changes_made.append(f"✓ Updated OCR scale to 6x at line {i+1}")
        break

# 2. Update column width (field column smaller)
for i, line in enumerate(lines):
    if 'self.json_tree.column("field"' in line and 'width=' in line:
        lines[i] = '        self.json_tree.column("field", width=120, minwidth=100)\n'
        changes_made.append(f"✓ Field column width to 120px at line {i+1}")
        break

# 3. Update patterns dictionary with all our improvements
for i, line in enumerate(lines):
    if 'patterns = {' in line.strip() and i > 1050:
        # Find the end of patterns dict
        end_idx = i
        for j in range(i, i+100):
            if lines[j].strip() == '}' and 'Try each pattern' in lines[j+2]:
                end_idx = j
                break
        
        # Replace with improved patterns
        new_patterns = [
            "        patterns = {\n",
            "            'parcel_number': [\n",
            "                r'Parcel[:\\s#]*(\\d+)',\n",
            "                r'(\\d{10})',\n",
            "            ],\n",
            "            'property_name': [\n",
            "                r'[Pp]ropary\\s*name[:\\s]*([^\\n]+)',\n",
            "                r'[Pp]roperty\\s*name[:\\s]*([^\\n]+)',\n",
            "            ],\n",
            "            'jurisdiction': [\n",
            "                r'[Jj]uracicion[:\\s]*([^\\n]+)',\n",
            "                r'[Jj]urisdic[t]?ion[:\\s]*([^\\n]+)',\n",
            "                r'(SEATTLE|BELLEVUE|RENTON|KENT)',\n",
            "            ],\n",
            "            'taxpayer_name': [\n",
            "                r'[Tt]axpayer\\s*name[:\\s]*([^\\n]+)',\n",
            "            ],\n",
            "            'address': [\n",
            "                r'[Aa]gora[:\\s]*([^\\n]+)',\n",
            "                r'[Aa]ddress[:\\s]*([^\\n]+)',\n",
            "                r'[Aa]derass[:\\s]*([^\\n]+)',\n",
            "            ],\n",
            "            'appraised_value': [\n",
            "                r'[Aa]ppraised\\s*value[:\\s]*(\\$?[\\d,]+)',\n",
            "            ],\n",
            "            'lot_area': [\n",
            "                r'[Ll]ot\\s*aren[:\\s]*([\\d,\\.]+)',\n",
            "                r'[Ll]ot\\s*area[:\\s]*([\\d,\\.]+)',\n",
            "            ],\n",
            "            'levy_code': [\n",
            "                r'(\\d{4})\\s*\\n+\\s*[Ll]avy\\s*cade:',\n",
            "                r'(\\d{4})\\s*\\n+\\s*[Ll]evy\\s*code:',\n",
            "                r'[Ll]avy\\s*cade[:\\s]+(\\d+)',\n",
            "                r'[Ll]evy\\s*code[:\\s]+(\\d+)',\n",
            "            ],\n",
            "            'num_units': [\n",
            "                r'(\\d+)\\s*\\n+\\s*#\\s*at\\s*unks:',\n",
            "                r'(\\d+)\\s*\\n+\\s*#\\s*of\\s*units:',\n",
            "                r'#\\s*at\\s*unks[:\\s]+(\\d+)',\n",
            "                r'#\\s*of\\s*units[:\\s]+(\\d+)',\n",
            "                r'#\\s*at\\s*unks[:\\s]*\\n+\\s*([^\\n]+?(?=\\s*\\n))',\n",
            "            ],\n",
            "            'num_buildings': [\n",
            "                r'#\\s*of\\s*buildings[:\\s]+(\\d+)',\n",
            "            ],\n",
            "        }\n",
        ]
        
        lines = lines[:i] + new_patterns + lines[end_idx+1:]
        changes_made.append(f"✓ Updated patterns dictionary with OCR typo handling")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n" + "\n".join(changes_made))
print("\n✓ Re-applied all improvements!")
