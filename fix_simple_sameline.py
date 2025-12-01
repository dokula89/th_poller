#!/usr/bin/env python3
"""Simple same-line matching - label: value on SAME line"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find patterns dict
start_idx = None
end_idx = None

for i, line in enumerate(lines):
    if 'patterns = {' in line.strip():
        start_idx = i
    if start_idx is not None and line.strip() == '}' and i > start_idx:
        if i + 2 < len(lines) and 'Try each pattern' in lines[i+2]:
            end_idx = i
            break

if start_idx is None or end_idx is None:
    print("ERROR: Could not find patterns dictionary")
    exit(1)

# Simple patterns - match label and value on same line OR next line
new_patterns_lines = [
    "        patterns = {\n",
    "            'parcel_number': [\n",
    "                r'Parcel[:\\s#]*(\\d+)',\n",
    "                r'(\\d{10})',  # 10-digit number\n",
    "            ],\n",
    "            'property_name': [\n",
    "                r'[Pp]ropary\\s*name[:\\s]*([^\\n]+)',  # OCR: Propary name: VALUE\n",
    "                r'[Pp]roperty\\s*name[:\\s]*([^\\n]+)',\n",
    "            ],\n",
    "            'jurisdiction': [\n",
    "                r'[Jj]uracicion[:\\s]*([^\\n]+)',  # OCR: Juracicion: VALUE\n",
    "                r'[Jj]urisdic[t]?ion[:\\s]*([^\\n]+)',\n",
    "                r'(SEATTLE|BELLEVUE|RENTON|KENT)',  # Uppercase city names\n",
    "            ],\n",
    "            'taxpayer_name': [\n",
    "                r'[Tt]axpayer\\s*name[:\\s]*([^\\n]+)',  # Taxpayer name: VALUE\n",
    "            ],\n",
    "            'address': [\n",
    "                r'[Aa]gora[:\\s]*([^\\n]+)',  # OCR: Agora: VALUE\n",
    "                r'[Aa]ddress[:\\s]*([^\\n]+)',\n",
    "                r'[Aa]derass[:\\s]*([^\\n]+)',\n",
    "            ],\n",
    "            'appraised_value': [\n",
    "                r'[Aa]ppraised\\s*value[:\\s]*(\\$?[\\d,]+)',\n",
    "            ],\n",
    "            'lot_area': [\n",
    "                r'[Ll]ot\\s*aren[:\\s]*([\\d,\\.]+)',  # OCR: Lot aren\n",
    "                r'[Ll]ot\\s*area[:\\s]*([\\d,\\.]+)',\n",
    "            ],\n",
    "            'levy_code': [\n",
    "                r'[Ll]avy\\s*cade[:\\s]*(\\d+)',  # OCR: Lavy cade\n",
    "                r'[Ll]evy\\s*code[:\\s]*(\\d+)',\n",
    "            ],\n",
    "            'num_units': [\n",
    "                r'#\\s*at\\s*unks[:\\s]*(\\d+)',  # OCR: # at unks\n",
    "                r'#\\s*of\\s*units[:\\s]*(\\d+)',\n",
    "            ],\n",
    "            'num_buildings': [\n",
    "                r'#\\s*of\\s*buildings[:\\s]*(\\d+)',\n",
    "            ],\n",
    "        }\n",
]

# Replace
lines = lines[:start_idx] + new_patterns_lines + lines[end_idx+1:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✓ Replaced with SIMPLE same-line patterns")
print("\nAll patterns now: LABEL: VALUE on same line")
print("Using [^\\n]+ to capture everything after the colon until newline")
