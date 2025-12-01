#!/usr/bin/env python3
"""Increase OCR upscaling from 4x to 8x for better recognition"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and update scale_factor
for i, line in enumerate(lines):
    if 'scale_factor = 4' in line and '220x140' in line:
        lines[i] = '            scale_factor = 8  # 8x upscale: 220x140 -> 1760x1120 for better recognition\n'
        print(f"✓ Updated scale_factor from 4x to 8x at line {i+1}")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ OCR upscaling increased from 4x to 8x!")
print("This will make the popup 1760x1120 pixels for much better text recognition")
