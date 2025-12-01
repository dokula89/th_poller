#!/usr/bin/env python3
"""Fix OCR extraction patterns based on actual OCR output"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Add "Agora" pattern for address (OCR reads "Address" as "Agora")
old_address = """            'address': [
                r'[Aa]ddress[:\s]*([^\n]+)',
                r'[Aa]derass[:\s]*([^\n]+)',  # OCR often reads 'dd' as 'der'
            ],"""

new_address = """            'address': [
                r'[Aa]ddress[:\s]*([^\n]+)',
                r'[Aa]derass[:\s]*([^\n]+)',  # OCR often reads 'dd' as 'der'
                r'[Aa]gora[:\s]*([^\n]+)',  # OCR typo: "Address" -> "Agora"
            ],"""

if old_address in content:
    content = content.replace(old_address, new_address)
    print("✓ Added 'Agora' pattern for address extraction")
else:
    print("✗ Could not find address pattern to update")

# Fix 2: Update property_name to handle "Propary" typo
old_property = """            'property_name': [
                r'[Pp]roperty\s*name[:\s]*([^\n]+)',
                r'[Pp]roperty[:\s]*([^\n]+)',
                r'name[:\s]*([A-Z][A-Za-z\s]+)',  # Flexible - anything after "name:"
            ],"""

new_property = """            'property_name': [
                r'[Pp]roperty\s*name[:\s]*([^\n]+)',
                r'[Pp]roperty[:\s]*([^\n]+)',
                r'[Pp]ropary\s*name[:\s]*([^\n]+)',  # OCR typo: "Property" -> "Propary"
                r'name[:\s]*([A-Z][A-Za-z\s]+)',  # Flexible - anything after "name:"
            ],"""

if old_property in content:
    content = content.replace(old_property, new_property)
    print("✓ Added 'Propary' pattern for property_name extraction")
else:
    print("✗ Could not find property_name pattern to update")

# Fix 3: Update jurisdiction to handle "Juracicion" typo
old_jurisdiction = """            'jurisdiction': [
                r'[Jj]urisdic[t]?ion[:\s]*([^\n]+)',  # Flexible spelling
                r'(SEATTLE|Seattle|Bellevue|Renton|Kent)',  # Common jurisdictions with capture group
            ],"""

new_jurisdiction = """            'jurisdiction': [
                r'[Jj]urisdic[t]?ion[:\s]*([^\n]+)',  # Flexible spelling
                r'[Jj]uracicion[:\s]*([^\n]+)',  # OCR typo: "Jurisdiction" -> "Juracicion"
                r'(SEATTLE|Seattle|Bellevue|Renton|Kent)',  # Common jurisdictions with capture group
            ],"""

if old_jurisdiction in content:
    content = content.replace(old_jurisdiction, new_jurisdiction)
    print("✓ Added 'Juracicion' pattern for jurisdiction extraction")
else:
    print("✗ Could not find jurisdiction pattern to update")

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ OCR patterns updated!")
print("Close and restart the automation window, then try again.")
