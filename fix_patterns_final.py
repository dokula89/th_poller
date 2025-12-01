#!/usr/bin/env python3
"""Fix ALL patterns to only match text on SAME line - line by line approach"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the patterns dictionary and replace it completely
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'patterns = {' in line.strip():
        start_idx = i
    if start_idx is not None and line.strip() == '}' and i > start_idx:
        # This is likely the end of patterns dict
        # Check if next line has "# Try each pattern"
        if i + 2 < len(lines) and 'Try each pattern' in lines[i+2]:
            end_idx = i
            break

if start_idx is None or end_idx is None:
    print("ERROR: Could not find patterns dictionary")
    exit(1)

print(f"Found patterns dict from line {start_idx+1} to {end_idx+1}")

# Create new patterns with same-line matching only
new_patterns_lines = [
    "        patterns = {\n",
    "            'parcel_number': [\n",
    "                r'Parcel[:\\s#]*(\\d+)',\n",
    "                r'Parcel[^\\d]*(\\d{10})',\n",
    "                r'(\\d{10})',  # Just look for 10-digit number\n",
    "            ],\n",
    "            'property_name': [\n",
    "                r'[Pp]roperty\\s*name[:\\s]+([^\\n:]+?)(?=\\s*$)',  # Only text on SAME line\n",
    "                r'[Pp]ropary\\s*name[:\\s]+([^\\n:]+?)(?=\\s*$)',  # OCR typo\n",
    "            ],\n",
    "            'jurisdiction': [\n",
    "                r'[Jj]urisdic[t]?ion[:\\s]+([^\\n]+?)(?=\\s*$)',  # Only text on SAME line\n",
    "                r'[Jj]uracicion[:\\s]+([^\\n]+?)(?=\\s*$)',  # OCR typo\n",
    "                r'(SEATTLE|Seattle|Bellevue|Renton|Kent)',  # Common jurisdictions\n",
    "            ],\n",
    "            'taxpayer_name': [\n",
    "                r'[Tt]axpayer\\s*name[:\\s]+([^\\n]+?)(?=\\s*$)',  # Only text on SAME line\n",
    "                r'[Tt]axpayer[:\\s]+([^\\n]+?)(?=\\s*$)',\n",
    "            ],\n",
    "            'address': [\n",
    "                r'[Aa]ddress[:\\s]+\\$?([^\\n]+?)(?=\\s*$)',  # Only text on SAME line, strip $\n",
    "                r'[Aa]derass[:\\s]+\\$?([^\\n]+?)(?=\\s*$)',  # OCR typo\n",
    "                r'[Aa]gora[:\\s]+\\$?([^\\n]+?)(?=\\s*$)',  # OCR typo: Address -> Agora\n",
    "            ],\n",
    "            'appraised_value': [\n",
    "                r'[Aa]ppraised\\s*value[:\\s]+\\$?([\\d,]+)',  # Numbers on SAME line\n",
    "                r'[Aa]ppraised[:\\s]+\\$?([\\d,]+)',\n",
    "            ],\n",
    "            'lot_area': [\n",
    "                r'[Ll]ot\\s*area[:\\s]+([\\d,\\.]+)',  # Numbers on SAME line\n",
    "                r'[Ll]ot[:\\s]+([\\d,\\.]+)',\n",
    "                r'[Ll]oams[:\\s]+([\\d,\\.]+)',  # OCR typo\n",
    "                r'[Ll]ot\\s*aren[:\\s]+([\\d,\\.]+)',  # OCR typo: area -> aren\n",
    "            ],\n",
    "            'levy_code': [\n",
    "                r'[Ll]evy\\s*code[:\\s]+(\\d+)',  # Numbers on SAME line\n",
    "                r'[Ll]evy[:\\s]+(\\d+)',\n",
    "                r'[Ll]avycode[:\\s]+(\\d+)',  # OCR typo\n",
    "                r'[Ll]avy\\s*cade[:\\s]+(\\d+)',  # OCR typo: levy code -> lavy cade\n",
    "            ],\n",
    "            'num_units': [\n",
    "                r'#\\s*of\\s*units[:\\s]+(\\d+)',  # Numbers on SAME line\n",
    "                r'of\\s*units[:\\s]+(\\d+)',\n",
    "                r'units[:\\s]+(\\d+)',\n",
    "                r'#\\s*at\\s*unks[:\\s]+(\\d+)',  # OCR typo: \"# of units\" -> \"# at unks\"\n",
    "            ],\n",
    "            'num_buildings': [\n",
    "                r'#\\s*of\\s*buildings[:\\s]+(\\d+)',  # Numbers on SAME line\n",
    "                r'of\\s*buildings[:\\s]+(\\d+)',\n",
    "                r'buildings[:\\s]+(\\d+)',\n",
    "                r'[Rr]oof\\s*buildings[:\\s]+(\\d+)',  # OCR typo\n",
    "            ],\n",
    "        }\n",
]

# Replace the patterns section
lines = lines[:start_idx] + new_patterns_lines + lines[end_idx+1:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✓ Replaced patterns dictionary (lines {start_idx+1} to {end_idx+1})")
print("\n✓ ALL patterns now only match text on the SAME line!")
print("\nKey improvements:")
print("  - Property name won't match 'Juracicion:' from next line")
print("  - Address will strip $ character")
print("  - Added 'lavy cade' pattern for levy_code")
print("  - Added '# at unks' pattern for num_units")
print("\nClose and restart window!")
