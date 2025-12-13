import re
import os

# Tables to search for
tables_found = set()

# Search patterns
patterns = [
    r'FROM\s+[`"]?(\w+)[`"]?',
    r'INTO\s+[`"]?(\w+)[`"]?',
    r'UPDATE\s+[`"]?(\w+)[`"]?',
    r'TABLE\s+[`"]?(\w+)[`"]?',
    r'JOIN\s+[`"]?(\w+)[`"]?',
]

ignore_words = {'if', 'the', 'a', 'to', 'is', 'in', 'it', 'as', 'be', 'or', 'on', 'at', 'by', 'an', 
                'no', 'so', 'we', 'do', 'my', 'up', 'go', 'me', 'he', 'am', 'of', 'for', 'not', 
                'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'you', 'day', 'get', 
                'has', 'him', 'his', 'how', 'its', 'let', 'may', 'new', 'now', 'old', 'see', 
                'two', 'way', 'who', 'boy', 'did', 'any', 'but', 'set', 'use', 'and', 'are', 
                'own', 'this', 'that', 'with', 'have', 'will', 'your', 'from', 'they', 'been',
                'call', 'first', 'could', 'water', 'find', 'long', 'down', 'side', 'make',
                'each', 'made', 'live', 'back', 'only', 'come', 'over', 'such', 'take', 'year',
                'list', 'file', 'time', 'data', 'name', 'here', 'line', 'text', 'value', 'item',
                'self', 'none', 'true', 'false', 'error', 'table', 'result', 'cursor', 'conn',
                'rows', 'cols', 'type', 'where', 'values', 'exists', 'like', 'select', 'insert',
                'delete', 'count', 'into', 'column', 'columns', 'drop', 'create', 'index'}

for filename in os.listdir('.'):
    if filename.endswith('.py'):
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                for pattern in patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for m in matches:
                        if m and len(m) > 2 and not m.isdigit() and m.lower() not in ignore_words:
                            tables_found.add(m.lower())
        except Exception as e:
            print(f"Error reading {filename}: {e}")

# Filter likely table names (those that look like database table names)
likely_tables = sorted([t for t in tables_found if not t.startswith('_') and len(t) > 3])
print('Likely table references found in Python files:')
for t in likely_tables:
    print(f'  {t}')
