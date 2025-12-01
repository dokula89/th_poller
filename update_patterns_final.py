"""Update patterns in parcel_automation.py with improved OCR patterns"""

# Read file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find patterns = { line
pattern_start = None
for i, line in enumerate(lines):
    if 'patterns = {' in line:
        pattern_start = i
        break

if pattern_start is None:
    print("ERROR: Could not find patterns dictionary")
    exit(1)

# Find the closing brace for patterns dict
pattern_end = None
brace_count = 0
for i in range(pattern_start, len(lines)):
    for char in lines[i]:
        if char == '{':
            brace_count += 1
        elif char == '}':
            brace_count -= 1
            if brace_count == 0:
                pattern_end = i
                break
    if pattern_end:
        break

if pattern_end is None:
    print("ERROR: Could not find end of patterns dictionary")
    exit(1)

# New improved patterns
new_pattern_lines = [
    "        patterns = {\n",
    "            'parcel_number': [\n",
    "                r'Parcel[:\s#]*([0-9A-Z]+)',\n",
    "                r'([0-9A-Z]{9,})',\n",
    "            ],\n",
    "            'property_name': [\n",
    "                r'[Pp]roperty\s*name[:\s]*([A-Z][^\\n]+(?:\\n[A-Z][^\\n]+)?)',\n",
    "                r'[Pp]ropertyname[:\s]*([A-Z][^\\n]+)',\n",
    "                r'[Pp]ropary\s*name[:\s]*([^\\n]+)',\n",
    "            ],\n",
    "            'jurisdiction': [\n",
    "                r'[Jj]uradiction[:\s]*([^\\n]+)',\n",
    "                r'[Jj]uracicion[:\s]*([^\\n]+)',\n",
    "                r'[Jj]urisdic[t]?ion[:\s]*([^\\n]+)',\n",
    "                r'(SEATTLE|BELLEVUE|RENTON|KENT|AUBURN|FEDERAL\s*WAY)',\n",
    "            ],\n",
    "            'taxpayer_name': [\n",
    "                r'[Tt]ax[xy]payer\s*name[:\s]*([^\\n]+)',\n",
    "                r'[Tt]axypayername[:\s]*([^\\n]+)',\n",
    "                r'[Tt]aspeyer\s*name[:\s]*([^\\n]+)',\n",
    "            ],\n",
    "            'address': [\n",
    "                r'[Aa]ddress[:\s]*([^\\n]+)',\n",
    "                r'[Aa]gora[:\s]*([^\\n]+)',\n",
    "                r'[Aa]derass[:\s]*([^\\n]+)',\n",
    "                r'([\$]?\\d+[A-Z]?\s+[A-Z0-9\s]+(?:ST|AVE|RD|WAY|DR|BLVD|PL|LN|CT)[^\\n]*)',\n",
    "            ],\n",
    "            'appraised_value': [\n",
    "                r'[Aa]ppraised\s*value[:\s]*\$?([\\d,]+)',\n",
    "                r'[Aa]ppraised\s*valve[:\s]*\$?([\\d,]+)',\n",
    "            ],\n",
    "            'lot_area': [\n",
    "                r'[Ll]et\s*area[:\s]*([\\d,\\.]+)',\n",
    "                r'[Ll]etarea[:\s]*([\\d,\\.]+)',\n",
    "                r'[Ll]ot\s*aren[:\s]*([\\d,\\.]+)',\n",
    "                r'[Ll]ot\s*area[:\s]*([\\d,\\.]+)',\n",
    "            ],\n",
    "            'levy_code': [\n",
    "                r'[Ll]avy\s*code[:\s]+([O0-9]{3,4})',\n",
    "                r'[Ll]avycode[:\s]+([O0-9]{3,4})',\n",
    "                r'[Ll]evy\s*code[:\s]+([O0-9]{3,4})',\n",
    "                r'([O0-9]{4})\s*\\n+\s*[Ll]avy\s*code:',\n",
    "                r'[Ll]avy\s*cade[:\s]+([O0-9]+)',\n",
    "            ],\n",
    "            'num_units': [\n",
    "                r'[Ff]ot\s*unts[:\s]+(\\d+)',\n",
    "                r'[Ff]otunts[:\s]+(\\d+)',\n",
    "                r'#\s*of\s*units[:\s]+(\\d+)',\n",
    "                r'(\\d+)\s*\\n+\s*#\s*of\s*units:',\n",
    "                r'#\s*at\s*unks[:\s]+(\\d+)',\n",
    "            ],\n",
    "            'num_buildings': [\n",
    "                r'[Ss]of\s*buikiings[:\s]+(\\d+)',\n",
    "                r'[Ss]ofbuikiings[:\s]+(\\d+)',\n",
    "                r'#\s*of\s*buildings[:\s]+(\\d+)',\n",
    "                r'#\s*at\s*buildings[:\s]+(\\d+)',\n",
    "            ],\n",
    "        }\n",
]

# Replace the patterns section
lines = lines[:pattern_start] + new_pattern_lines + lines[pattern_end+1:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Updated patterns dictionary with improved OCR patterns from image analysis")
print("  Added patterns based on real OCR output:")
print("  - Alphanumeric parcel numbers (TB3G800C06)")
print("  - Multi-line property names")
print("  - OCR typos: Juradiktion, Taxypayer, Letarea, Fotunts, Sofbuikiings")
print("  - No-space variations: Propertyname, Letarea, etc.")
print("  - Letter O in levy codes (O13)")
