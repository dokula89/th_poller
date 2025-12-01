#!/usr/bin/env python3
"""Fix levy_code and num_units to capture values between labels"""

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

# Update levy_code pattern to look for number BEFORE the label
for i in range(start_idx, end_idx):
    if "'levy_code': [" in lines[i]:
        # Replace patterns - look for a 4-digit number that appears before "Lavy cade:" or "Levy code:"
        new_patterns = [
            "            'levy_code': [\n",
            "                r'(\\d{4})\\s*\\n+\\s*[Ll]avy\\s*cade:',  # Number BEFORE label\n",
            "                r'(\\d{4})\\s*\\n+\\s*[Ll]evy\\s*code:',  # Number BEFORE label\n",
            "                r'[Ll]avy\\s*cade[:\\s]+(\\d+)',  # After label (fallback)\n",
            "                r'[Ll]evy\\s*code[:\\s]+(\\d+)',  # After label (fallback)\n",
            "            ],\n",
        ]
        # Find end of levy_code patterns
        end_pattern = i + 1
        while end_pattern < end_idx and '],\n' not in lines[end_pattern]:
            end_pattern += 1
        end_pattern += 1  # Include the ],
        
        # Replace
        lines = lines[:i] + new_patterns + lines[end_pattern:]
        print(f"✓ Updated levy_code patterns (lines {i+1}-{end_pattern})")
        # Adjust end_idx
        end_idx = end_idx - (end_pattern - i) + len(new_patterns)
        break

# Update num_units pattern to be more flexible
for i in range(start_idx, end_idx):
    if "'num_units': [" in lines[i]:
        # Look for ANY digit before or after the label
        new_patterns = [
            "            'num_units': [\n",
            "                r'(\\d+)\\s*\\n+\\s*#\\s*at\\s*unks:',  # Number BEFORE label\n",
            "                r'(\\d+)\\s*\\n+\\s*#\\s*of\\s*units:',  # Number BEFORE label\n",
            "                r'#\\s*at\\s*unks[:\\s]+(\\d+)',  # After label (fallback)\n",
            "                r'#\\s*of\\s*units[:\\s]+(\\d+)',  # After label (fallback)\n",
            "            ],\n",
        ]
        # Find end of num_units patterns
        end_pattern = i + 1
        while end_pattern < end_idx and '],\n' not in lines[end_pattern]:
            end_pattern += 1
        end_pattern += 1  # Include the ],
        
        # Replace
        lines = lines[:i] + new_patterns + lines[end_pattern:]
        print(f"✓ Updated num_units patterns (lines {i+1}-{end_pattern})")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Updated levy_code and num_units to look for values BEFORE labels!")
print("This handles the weird layout where values appear between field labels.")
