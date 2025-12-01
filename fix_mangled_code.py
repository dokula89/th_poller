#!/usr/bin/env python3
"""Fix the mangled clearing code"""

# Read the file
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find and fix the mangled section around line 1371-1374
for i in range(1365, 1380):
    if i < len(lines) and 'Clearing parcels_data.json' in lines[i]:
        # Check if the next lines are mangled
        if 'with open(json_path' in lines[i+1] and not lines[i+1].strip().startswith('with'):
            # Fix the indentation
            print(f"Found mangled code at line {i+1}")
            
            # Replace lines i through i+4 with properly formatted code
            new_lines = [
                lines[i],  # Keep the append_log line
                "                self.window.after(0, lambda: self.update_status(\"✓ Clearing JSON after successful upload\", 9))\n",
                "                with open(json_path, 'w', encoding='utf-8') as f:\n",
                "                    json.dump([], f)\n",
            ]
            
            # Find where the mangled section ends (look for the next proper line)
            end_idx = i + 1
            while end_idx < len(lines) and 'Refreshing parent table' not in lines[end_idx]:
                if '))' in lines[end_idx] and 'text=' not in lines[end_idx]:
                    end_idx += 1
                    break
                end_idx += 1
            
            # Replace the mangled section
            lines = lines[:i] + new_lines + lines[end_idx:]
            print(f"✓ Fixed lines {i+1} to {end_idx}")
            break

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("\n✓ Fixed mangled clearing code")
