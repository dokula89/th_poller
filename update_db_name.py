import os
import re

# Find all .py files with 'database="offta_local"' 
files_to_update = []
for f in os.listdir('.'):
    if f.endswith('.py'):
        with open(f, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            if 'database="offta_local"' in content:
                files_to_update.append(f)

print(f'Files with offta references: {len(files_to_update)}')
for f in sorted(files_to_update):
    print(f'  {f}')

# Now update them - but ONLY for localhost connections, not remote
print('\nUpdating files...')
for filename in files_to_update:
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Count replacements
    original = content
    
    # Replace database="offta_local" with database="offta_local" ONLY when near localhost
    # We need to be careful not to replace the remote database references
    
    # Pattern 1: host="localhost"... database="offta_local" (within same connect call)
    # Pattern 2: host='localhost'... database='offta'
    
    # Simple approach: replace all 'database="offta"' that are NOT preceded by '172.104.206.182'
    # Split by lines and check context
    
    lines = content.split('\n')
    new_lines = []
    in_remote_block = False
    
    for i, line in enumerate(lines):
        # Check if we're in a remote connection context
        if '172.104.206.182' in line:
            in_remote_block = True
        
        # If we find localhost, we're back to local
        if 'localhost' in line:
            in_remote_block = False
        
        # Only replace if not in remote block
        if not in_remote_block and 'database="offta_local"' in line:
            line = line.replace('database="offta_local"', 'database="offta_local"')
        
        new_lines.append(line)
    
    new_content = '\n'.join(new_lines)
    
    if new_content != original:
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(new_content)
        count = original.count('database="offta_local"') - new_content.count('database="offta_local"')
        print(f'  Updated {filename}: {count} replacements')
    else:
        print(f'  {filename}: no local references found')

print('\nDone!')
