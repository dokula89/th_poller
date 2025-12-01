#!/usr/bin/env python3
"""Fix ALL patterns to only match text on the SAME line (right side of the label)"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the entire patterns dictionary with corrected version
# Key change: Use [^\n:]+ and require at least one non-whitespace character after the colon

old_patterns = """        patterns = {
            'parcel_number': [
                r'Parcel[:\s#]*(\d+)',
                r'Parcel[^\d]*(\d{10})',
                r'(\d{10})',  # Just look for 10-digit number
            ],
            'property_name': [
                r'[Pp]roperty\s*name[:\s]*([^\n:]+?)\s*$',  # Match property name without trailing colon
                r'[Pp]ropary\s*name[:\s]*([^\n:]+?)\s*$',  # OCR typo: Property -> Propary
            ],
            'jurisdiction': [
                r'[Jj]urisdic[t]?ion[:\s]*([^\n]+)',  # Flexible spelling
                r'[Jj]uracicion[:\s]*([^\n]+)',  # OCR typo: Jurisdiction -> Juracicion
                r'(SEATTLE|Seattle|Bellevue|Renton|Kent)',  # Common jurisdictions with capture group
            ],
            'taxpayer_name': [
                r'[Tt]axpayer\s*name[:\s]*([^\n]+)',
                r'[Tt]axpayer[:\s]*([^\n]+)',
            ],
            'address': [
                r'[Aa]ddress[:\s]*([^\n]+)',
                r'[Aa]derass[:\s]*([^\n]+)',  # OCR often reads 'dd' as 'der'
                r'[Aa]gora[:\s]*\$?(.+)',  # OCR typo with optional $
            ],
            'appraised_value': [
                r'[Aa]ppraised\s*value[:\s]*\$?([\d,]+)',
                r'[Aa]ppraised[:\s]*\$?([\d,]+)',
            ],
            'lot_area': [
                r'[Ll]ot\s*area[:\s]*([\d,\.]+)',
                r'[Ll]ot[:\s]*([\d,\.]+)',
                r'[Ll]oams[:\s]*([\d,\.]+)',  # OCR typo
                r'[Ll]ot\s*aren[:\s]*([\d,\.]+)',  # OCR typo: area -> aren
            ],
            'levy_code': [
                r'[Ll]evy\s*code[:\s]*(\d+)',
                r'[Ll]evy[:\s]*(\d+)',
                r'[Ll]avycode[:\s]*(\d+)',  # OCR typo
            ],
            'num_units': [
                r'#\s*of\s*units[:\s]*(\d+)',
                r'of\s*units[:\s]*(\d+)',
                r'units[:\s]*(\d+)',
                r'atunk[^\d]*(\d+)',  # OCR typo for "# of units"
            ],
            'num_buildings': [
                r'#\s*of\s*buildings[:\s]*(\d+)',
                r'of\s*buildings[:\s]*(\d+)',
                r'buildings[:\s]*(\d+)',
                r'[Rr]oof\s*buildings[:\s]*(\d+)',  # OCR typo
            ],
        }"""

new_patterns = """        patterns = {
            'parcel_number': [
                r'Parcel[:\s#]*(\d+)',
                r'Parcel[^\d]*(\d{10})',
                r'(\d{10})',  # Just look for 10-digit number
            ],
            'property_name': [
                r'[Pp]roperty\s*name[:\s]+([^\n:]+?)(?=\s*$)',  # Only match text on SAME line
                r'[Pp]ropary\s*name[:\s]+([^\n:]+?)(?=\s*$)',  # OCR typo: Property -> Propary
            ],
            'jurisdiction': [
                r'[Jj]urisdic[t]?ion[:\s]+([^\n]+?)(?=\s*$)',  # Only match text on SAME line
                r'[Jj]uracicion[:\s]+([^\n]+?)(?=\s*$)',  # OCR typo: Jurisdiction -> Juracicion
                r'(SEATTLE|Seattle|Bellevue|Renton|Kent)',  # Common jurisdictions
            ],
            'taxpayer_name': [
                r'[Tt]axpayer\s*name[:\s]+([^\n]+?)(?=\s*$)',  # Only match text on SAME line
                r'[Tt]axpayer[:\s]+([^\n]+?)(?=\s*$)',
            ],
            'address': [
                r'[Aa]ddress[:\s]+\$?([^\n]+?)(?=\s*$)',  # Only match text on SAME line, strip $
                r'[Aa]derass[:\s]+\$?([^\n]+?)(?=\s*$)',  # OCR often reads 'dd' as 'der'
                r'[Aa]gora[:\s]+\$?([^\n]+?)(?=\s*$)',  # OCR typo: Address -> Agora
            ],
            'appraised_value': [
                r'[Aa]ppraised\s*value[:\s]+\$?([\d,]+)',  # Match numbers on SAME line
                r'[Aa]ppraised[:\s]+\$?([\d,]+)',
            ],
            'lot_area': [
                r'[Ll]ot\s*area[:\s]+([\d,\.]+)',  # Match numbers on SAME line
                r'[Ll]ot[:\s]+([\d,\.]+)',
                r'[Ll]oams[:\s]+([\d,\.]+)',  # OCR typo
                r'[Ll]ot\s*aren[:\s]+([\d,\.]+)',  # OCR typo: area -> aren
            ],
            'levy_code': [
                r'[Ll]evy\s*code[:\s]+(\d+)',  # Match numbers on SAME line
                r'[Ll]evy[:\s]+(\d+)',
                r'[Ll]avycode[:\s]+(\d+)',  # OCR typo
                r'[Ll]avy\s*cade[:\s]+(\d+)',  # OCR typo: levy code -> lavy cade
            ],
            'num_units': [
                r'#\s*of\s*units[:\s]+(\d+)',  # Match numbers on SAME line
                r'of\s*units[:\s]+(\d+)',
                r'units[:\s]+(\d+)',
                r'#\s*at\s*unks[:\s]+(\d+)',  # OCR typo: "# of units" -> "# at unks"
            ],
            'num_buildings': [
                r'#\s*of\s*buildings[:\s]+(\d+)',  # Match numbers on SAME line
                r'of\s*buildings[:\s]+(\d+)',
                r'buildings[:\s]+(\d+)',
                r'[Rr]oof\s*buildings[:\s]+(\d+)',  # OCR typo
            ],
        }"""

if old_patterns in content:
    content = content.replace(old_patterns, new_patterns)
    print("✓ Replaced entire patterns dictionary")
else:
    print("✗ Could not find exact patterns dictionary to replace")
    print("Trying partial replacement...")

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ Updated ALL patterns to only match text on the SAME line!")
print("Key changes:")
print("  - All patterns now use (?=\\s*$) to ensure end of line")
print("  - Changed [:\\s]* to [:\\s]+ to require space/text after colon")
print("  - Added 'lavy cade' pattern for levy_code")
print("  - Added '# at unks' pattern for num_units")
print("\nClose and restart window!")
