"""Automatically inject batch processing methods into parcel_automation.py"""

# Read the methods
with open('batch_processing_methods.py', 'r', encoding='utf-8') as f:
    content = f.read()
    # Extract just the methods part
    methods_start = content.find('METHODS_TO_ADD = \'\'\'')
    methods_end = content.rfind('\'\'\'')
    methods_code = content[methods_start + 21:methods_end]

# Read parcel_automation.py
with open('parcel_automation.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the end of ParcelAutomationWindow class (before launch_parcel_automation function)
insert_line = None
for i in range(len(lines) - 1, -1, -1):
    if 'def launch_parcel_automation' in lines[i]:
        # Insert before this function
        insert_line = i - 1
        # Skip back past empty lines
        while insert_line > 0 and lines[insert_line].strip() == '':
            insert_line -= 1
        insert_line += 1
        break

if insert_line is None:
    print("ERROR: Could not find insertion point")
    exit(1)

# Insert the methods
method_lines = methods_code.split('\\n')
lines_to_insert = [line + '\\n' for line in method_lines]

lines = lines[:insert_line] + ['\\n'] + lines_to_insert + ['\\n'] + lines[insert_line:]

# Write back
with open('parcel_automation.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Added batch processing methods to ParcelAutomationWindow class")
print("  - process_parcel_images_batch()")
print("  - process_with_openai_batch()")
print("  - extract_with_openai_vision()")
print("  - insert_batch_to_database()")
print("  - process_with_beautifulsoup()")
