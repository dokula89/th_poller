#!/usr/bin/env python3
"""Fix property_name to not match jurisdiction"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix: Update property_name patterns to be more specific and exclude trailing colons
for i, line in enumerate(lines):
    if "'property_name': [" in line:
        # Replace the patterns to exclude matches that end with colon
        # Find all pattern lines until the closing bracket
        patterns_end = None
        for j in range(i+1, min(i+10, len(lines))):
            if "],\n" in lines[j]:
                patterns_end = j
                break
        
        if patterns_end:
            # Replace with better patterns
            new_patterns = [
                "            'property_name': [\n",
                "                r'[Pp]roperty\\s*name[:\\s]*([^\\n:]+?)\\s*$',  # Match property name without trailing colon\n",
                "                r'[Pp]ropary\\s*name[:\\s]*([^\\n:]+?)\\s*$',  # OCR typo: Property -> Propary\n",
                "            ],\n"
            ]
            
            # Replace lines from i to patterns_end+1
            lines = lines[:i] + new_patterns + lines[patterns_end+1:]
            print(f"✓ Updated property_name patterns (lines {i+1}-{patterns_end+1})")
            break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Fixed property_name patterns to exclude trailing colons!")
print("Now it won't match 'Juracicion:' as the property name")
