"""
Apply improved OCR patterns from image analysis to parcel_automation.py
Based on actual OCR output from parcels_965.png and parcels_970.png
"""

import re

print("Applying improved OCR patterns to parcel_automation.py...")

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the patterns dictionary
pattern_start = content.find("'parcel_number': [")
if pattern_start == -1:
    print("ERROR: Could not find patterns dictionary")
    exit(1)

# Find the end of patterns dict (look for closing })
pattern_end = content.find("}", pattern_start)
# Make sure we get the right closing brace
brace_count = 1
pos = pattern_start
while brace_count > 0 and pos < len(content):
    pos += 1
    if content[pos] == '{':
        brace_count += 1
    elif content[pos] == '}':
        brace_count -= 1
pattern_end = pos

# New improved patterns based on actual OCR output
new_patterns = """'parcel_number': [
            r'Parcel[:\s]*([0-9A-Z]+)',  # Allow letters (TB3G800C06)
            r'Parcel.*?([0-9A-Z]{9,})',
        ],
        'present_use': [
            r'Present\s*use[:\s]*([^\n]+)',
            r'Prasent\s*use[:\s]*([^\n]+)',
            r'Presentuse[:\s]*([^\n]+)',  # OCR: no space
        ],
        'property_name': [
            r'[Pp]roperty\s*name[:\s]*([^\n]+(?:\n[A-Z][^\n]+)?)',  # Multi-line support
            r'[Pp]ropertyname[:\s]*([^\n]+)',  # OCR: no space
            r'[Pp]ropary\s*name[:\s]*([^\n]+)',
        ],
        'jurisdiction': [
            r'[Jj]uradiction[:\s]*([^\n]+)',  # OCR: Juradiktion
            r'[Jj]uracicion[:\s]*([^\n]+)',
            r'[Jj]urisdic[t]?ion[:\s]*([^\n]+)',
            r'(SEATTLE|BELLEVUE|RENTON|KENT|AUBURN|FEDERAL\s*WAY)',
        ],
        'taxpayer_name': [
            r'[Tt]ax[xy]payer\s*name[:\s]*([^\n]+)',  # OCR: Taxypayer
            r'[Tt]axypayername[:\s]*([^\n]+)',  # OCR: no space
            r'[Tt]aspeyer\s*name[:\s]*([^\n]+)',
        ],
        'address': [
            r'[Aa]ddress[:\s]*([^\n]+)',
            r'[Aa]gora[:\s]*([^\n]+)',  # OCR typo
            r'([\$]?\d+[A-Z]?\s+[A-Z0-9\s]+(?:ST|AVE|RD|WAY|DR|BLVD|PL|LN|CT)[^\n]*)',
        ],
        'appraised_value': [
            r'Appraised\s*value[:\s]*\$?([\d,]+)',
            r'Appraised\s*valve[:\s]*\$?([\d,]+)',
        ],
        'lot_area': [
            r'[Ll]et\s*area[:\s]*([\d,\.]+)',  # OCR: Letarea
            r'[Ll]etarea[:\s]*([\d,\.]+)',  # OCR: no space
            r'[Ll]ot\s*aren[:\s]*([\d,\.]+)',
            r'[Ll]ot\s*area[:\s]*([\d,\.]+)',
        ],
        'num_units': [
            r'[Ff]ot\s*unts[:\s]+([\d]+)',  # OCR: Fotunts
            r'[Ff]otunts[:\s]+([\d]+)',  # OCR: no space
            r'#\s*of\s*units[:\s]+([\d]+)',
            r'(\d+)\s*\n+\s*#\s*of\s*units:',
            r'#\s*at\s*unks[:\s]+([\d]+)',
        ],
        'num_buildings': [
            r'[Ss]of\s*buikiings[:\s]+([\d]+)',  # OCR: Sofbuikiings
            r'[Ss]ofbuikiings[:\s]+([\d]+)',  # OCR: no space
            r'#\s*of\s*buildings[:\s]+([\d]+)',
            r'#\s*at\s*buildings[:\s]+([\d]+)',
        ],
        'levy_code': [
            r'[Ll]avy\s*code[:\s]+([O0-9]{3,4})',  # OCR: O13 (letter O)
            r'[Ll]avycode[:\s]+([O0-9]{3,4})',  # OCR: no space
            r'[Ll]evy\s*code[:\s]+([O0-9]{3,4})',
            r'([O0-9]{4})\s*\n+\s*[Ll]avy\s*code:',
            r'[Ll]avy\s*cade[:\s]+([O0-9]+)',
        ],"""

# Replace the patterns
content = content[:pattern_start] + new_patterns + content[pattern_end:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Updated patterns dictionary with improved OCR patterns")
print("  - Added support for alphanumeric parcel numbers (TB3G800C06)")
print("  - Added multi-line property name support")
print("  - Added OCR typo patterns: Juradiktion, Taxypayer, Letarea, Fotunts, Sofbuikiings")
print("  - Added patterns for no-space OCR errors: Presentuse, Propertyname, etc.")
print("  - Added support for letter O in levy codes (O13 vs 0013)")
print("\n✓ All improvements applied!")
