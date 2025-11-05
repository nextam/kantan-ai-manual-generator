import os

def check_null_bytes(file_path):
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            if b'\x00' in content:
                count = content.count(b'\x00')
                return True, count
    except:
        pass
    return False, 0

# Check all Python files
problematic_files = []
for root, dirs, files in os.walk('src'):
    for file in files:
        if file.endswith('.py'):
            filepath = os.path.join(root, file)
            has_null, count = check_null_bytes(filepath)
            if has_null:
                problematic_files.append((filepath, count))

print("Files with null bytes:")
for filepath, count in problematic_files:
    print(f"  {filepath}: {count} null bytes")

if not problematic_files:
    print("  No files with null bytes found!")
