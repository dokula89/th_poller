import re
from pathlib import Path

def fix_imports(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix relative imports
    content = re.sub(r'from \.([\w_]+) import', r'from \1 import', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Fixed imports in {file_path}")

# Fix imports in all Python files
root = Path('.')
for py_file in root.glob('*.py'):
    if py_file.name != 'fix_imports.py':
        fix_imports(py_file)