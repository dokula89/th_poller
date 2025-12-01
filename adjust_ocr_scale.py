#!/usr/bin/env python3
"""Reduce upscaling to 6x - sweet spot for OCR"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and update scale_factor
for i, line in enumerate(lines):
    if 'scale_factor = 8' in line:
        lines[i] = '            scale_factor = 6  # 6x upscale: 220x140 -> 1320x840\n'
        print(f"✓ Updated scale_factor from 8x to 6x at line {i+1}")
        break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ OCR upscaling adjusted to 6x (sweet spot)")
