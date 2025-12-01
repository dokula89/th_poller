"""Add additional OCR typo patterns discovered from orange background testing"""

with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find patterns dictionary
pattern_start = None
for i, line in enumerate(lines):
    if "'parcel_number': [" in line:
        pattern_start = i
        break

if pattern_start is None:
    print("ERROR: Could not find parcel_number patterns")
    exit(1)

# Update specific patterns with new typos
replacements = [
    # Parcel -> Parcal
    (
        "                r'Parcel[:\s#]*([0-9A-Z]+)',\n",
        "                r'[Pp]arc[ae]l[:\s#]*([0-9A-Z]+)',  # Parcel or Parcal\n"
    ),
    # Present use -> Preseamtuse
    (
        "            'present_use': [\n",
        "            'present_use': [\n                r'[Pp]reseamtuse[:\s]*([^\\n]+)',  # OCR: Preseamtuse\n"
    ),
    # Jurisdiction -> Araacdion
    (
        "                r'[Jj]uradiction[:\s]*([^\\n]+)',\n",
        "                r'[Aa]raacdion[:\s]*([^\\n]+)',  # OCR: Araacdion\n                r'[Jj]uradiction[:\s]*([^\\n]+)',\n"
    ),
    # Taxpayer -> Taxpayer (already has variants, add more)
    (
        "                r'[Tt]ax[xy]payer\s*name[:\s]*([^\\n]+)',\n",
        "                r'[Tt]axpayer\s*name[:\s]*([^\\n]+)',  # Standard\n                r'[Tt]ax[xy]payer\s*name[:\s]*([^\\n]+)',  # Taxypayer\n"
    ),
    # Lot area variations
    (
        "                r'[Ll]et\s*area[:\s]*([\\d,\\.]+)',\n",
        "                r'[Ll]otarea[:\s]*([\\d,\\.]+)',  # OCR: no space\n                r'[Ll]et\s*area[:\s]*([\\d,\\.]+)',  # OCR: Letarea\n"
    ),
    # # of units -> #otunts
    (
        "                r'[Ff]ot\s*unts[:\s]+(\\d+)',\n",
        "                r'#ot\s*unts[:\s]+(\\d+)',  # OCR: #otunts\n                r'[Ff]ot\s*unts[:\s]+(\\d+)',  # OCR: Fotunts\n"
    ),
    # Apartment -> Apartmant, Aparitmant
    (
        "            'present_use': [\n",
        "            'present_use': [\n                r'[Pp]resent\s*use[:\s]*([^\\n]+)',\n"
    ),
]

# Read full content
content = ''.join(lines)

# Apply typo pattern additions directly to content
# Add Parcal pattern
content = content.replace(
    "r'Parcel[:\\s#]*([0-9A-Z]+)',",
    "r'[Pp]arc[ae]l[:\\s#]*([0-9A-Z]+)',  # Parcel or Parcal"
)

# Add Araacdion pattern  
content = content.replace(
    "r'[Jj]uradiction[:\\s]*([^\\n]+)',",
    "r'[Aa]raacdion[:\\s]*([^\\n]+)',  # OCR: Araacdion\n                r'[Jj]uradiction[:\\s]*([^\\n]+)',"
)

# Add #otunts pattern
content = content.replace(
    "r'[Ff]ot\\s*unts[:\\s]+(\\d+)',",
    "r'#ot\\s*unts[:\\s]+(\\d+)',  # OCR: #otunts\n                r'[Ff]ot\\s*unts[:\\s]+(\\d+)',"
)

# Add Preseamtuse pattern
if "r'Present\\s*use[:\\s]*([^\\n]+)'," in content:
    content = content.replace(
        "r'Present\\s*use[:\\s]*([^\\n]+)',",
        "r'[Pp]rese[an][mt]t?use[:\\s]*([^\\n]+)',  # Present/Preseamtuse/Prasent\n                r'Present\\s*use[:\\s]*([^\\n]+',"
    )

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✓ Added OCR typo patterns from orange background testing:")
print("  - Parcal (parcel typo)")
print("  - Araacdion (jurisdiction typo)")
print("  - #otunts (# of units typo)")
print("  - Preseamtuse (present use typo)")
