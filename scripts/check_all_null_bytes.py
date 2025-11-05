import os

def check_null_bytes_all_python():
    problematic = []
    for root, dirs, files in os.walk('.'):
        # Skip .venv and other virtual environments
        if '.venv' in root or 'venv' in root or '__pycache__' in root:
            continue
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'rb') as f:
                        content = f.read()
                        if b'\x00' in content:
                            count = content.count(b'\x00')
                            problematic.append((filepath, count))
                except:
                    pass
    
    return problematic

files = check_null_bytes_all_python()
if files:
    print("Files with null bytes:")
    for filepath, count in files:
        print(f"  {filepath}: {count} null bytes")
else:
    print("No files with null bytes found!")
