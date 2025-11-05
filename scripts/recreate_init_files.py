init_files = [
    'src/__init__.py',
    'src/api/__init__.py',
    'src/config/__init__.py',
    'src/core/__init__.py',
    'src/infrastructure/__init__.py',
    'src/middleware/__init__.py',
    'src/models/__init__.py',
    'src/services/__init__.py',
    'src/utils/__init__.py'
]

for filepath in init_files:
    # Write empty content as UTF-8
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write('')
    print(f"Created: {filepath}")

print("\nAll __init__.py files recreated successfully!")
