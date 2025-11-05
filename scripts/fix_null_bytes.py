import os

def fix_null_bytes(file_path):
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        if b'\x00' in content:
            # Remove null bytes
            cleaned_content = content.replace(b'\x00', b'')
            
            with open(file_path, 'wb') as f:
                f.write(cleaned_content)
            
            return True
    except Exception as e:
        print(f"Error fixing {file_path}: {e}")
        return False
    
    return False

# Fix all __init__.py files
fixed_count = 0
for root, dirs, files in os.walk('src'):
    for file in files:
        if file == '__init__.py':
            filepath = os.path.join(root, file)
            if fix_null_bytes(filepath):
                print(f"Fixed: {filepath}")
                fixed_count += 1

print(f"\nTotal files fixed: {fixed_count}")
