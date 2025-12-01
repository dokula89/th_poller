#!/usr/bin/env python3
"""Fix patterns - some fields are label-then-value, some are value-then-label"""

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

# Create corrected patterns
new_patterns_lines = [
    "        patterns = {\n",
    "            'parcel_number': [\n",
    "                r'Parcel[:\\s#]*(\\d+)',\n",
    "                r'Parcel[^\\d]*(\\d{10})',\n",
    "                r'(\\d{10})',  # Just look for 10-digit number\n",
    "            ],\n",
    "            'property_name': [\n",
    "                # VALUE comes BEFORE label: CIELO SOUTH... then Propary name:\n",
    "                r'([A-Z][A-Z0-9\\s]+[a-zA-Z]+)\\s*\\n+\\s*[Pp]ropary\\s*name:',  # OCR typo\n",
    "                r'([A-Z][A-Z0-9\\s]+[a-zA-Z]+)\\s*\\n+\\s*[Pp]roperty\\s*name:',\n",
    "                r'([A-Z][A-Z\\s]+)\\s*\\n+\\s*[Pp]ropary\\s*name:',\n",
    "            ],\n",
    "            'jurisdiction': [\n",
    "                # LABEL comes BEFORE value: Juracicion: then SEATTLE\n",
    "                r'[Jj]uracicion:\\s*\\n+\\s*([A-Z][A-Z\\s]+?)(?=\\s*\\n)',  # OCR typo\n",
    "                r'[Jj]urisdic[t]?ion:\\s*\\n+\\s*([A-Z][A-Z\\s]+?)(?=\\s*\\n)',\n",
    "                r'(SEATTLE|Seattle|Bellevue|Renton|Kent)',  # Fallback\n",
    "            ],\n",
    "            'taxpayer_name': [\n",
    "                # LABEL comes BEFORE value: Taxpayer name: then CIELO NORTH LLC\n",
    "                r'[Tt]axpayer\\s*name:\\s*\\n+\\s*([A-Z][A-Z0-9\\s]+?)(?=\\s*\\n)',\n",
    "                r'[Tt]axpayer:\\s*\\n+\\s*([A-Z][A-Z\\s]+?)(?=\\s*\\n)',\n",
    "            ],\n",
    "            'address': [\n",
    "                # LABEL comes BEFORE value: Agora: then $520 7TH AVE NE\n",
    "                r'[Aa]gora:\\s*\\n+\\s*([^\\n]+?)(?=\\s*\\n)',  # OCR typo: Address -> Agora\n",
    "                r'[Aa]ddress:\\s*\\n+\\s*([^\\n]+?)(?=\\s*\\n)',\n",
    "                r'[Aa]derass:\\s*\\n+\\s*([^\\n]+?)(?=\\s*\\n)',  # OCR typo\n",
    "            ],\n",
    "            'appraised_value': [\n",
    "                # LABEL comes BEFORE value: Appraised value: then $7,820,300\n",
    "                r'[Aa]ppraised\\s*value:\\s*\\n+\\s*(\\$?[\\d,]+)',\n",
    "                r'[Aa]ppraised:\\s*\\n+\\s*(\\$?[\\d,]+)',\n",
    "            ],\n",
    "            'lot_area': [\n",
    "                # LABEL comes BEFORE value: Lot aren: then 3415\n",
    "                r'[Ll]ot\\s*aren:\\s*\\n+\\s*([\\d,\\.]+)',  # OCR typo: area -> aren\n",
    "                r'[Ll]ot\\s*area:\\s*\\n+\\s*([\\d,\\.]+)',\n",
    "                r'[Ll]oams:\\s*\\n+\\s*([\\d,\\.]+)',  # OCR typo\n",
    "            ],\n",
    "            'levy_code': [\n",
    "                # LABEL comes BEFORE value: Lavy cade: then 0013\n",
    "                r'[Ll]avy\\s*cade:\\s*\\n+\\s*(\\d+)',  # OCR typo: levy code -> lavy cade\n",
    "                r'[Ll]evy\\s*code:\\s*\\n+\\s*(\\d+)',\n",
    "                r'[Ll]avycode:\\s*\\n+\\s*(\\d+)',\n",
    "            ],\n",
    "            'num_units': [\n",
    "                # LABEL comes BEFORE value: # at unks: then number\n",
    "                r'#\\s*at\\s*unks:\\s*\\n+\\s*(\\d+)',  # OCR typo: \"# of units\" -> \"# at unks\"\n",
    "                r'#\\s*of\\s*units:\\s*\\n+\\s*(\\d+)',\n",
    "                r'of\\s*units:\\s*\\n+\\s*(\\d+)',\n",
    "            ],\n",
    "            'num_buildings': [\n",
    "                # LABEL comes BEFORE value: # of buildings: then number\n",
    "                r'#\\s*of\\s*buildings:\\s*\\n+\\s*(\\d+)',\n",
    "                r'of\\s*buildings:\\s*\\n+\\s*(\\d+)',\n",
    "                r'buildings:\\s*\\n+\\s*(\\d+)',\n",
    "            ],\n",
    "        }\n",
]

# Replace patterns
lines = lines[:start_idx] + new_patterns_lines + lines[end_idx+1:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print(f"✓ Replaced patterns (lines {start_idx+1} to {end_idx+1})")
print("\n✓ Fixed pattern directions:")
print("  - Property name: VALUE before label (CIELO SOUTH... before Propary name:)")
print("  - Jurisdiction: LABEL before value (Juracicion: before SEATTLE)")
print("  - Taxpayer: LABEL before value (Taxpayer name: before CIELO NORTH LLC)")
print("  - Address: LABEL before value (Agora: before $520...)")
print("  - All others: LABEL before value")
print("\nClose and restart window!")
