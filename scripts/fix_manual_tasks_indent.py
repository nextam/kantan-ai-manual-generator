"""
Fix indentation in manual_tasks.py for app_context wrapping
"""

# Read the file
with open('src/workers/manual_tasks.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with "with app.app_context():" and fix indentation after it
fixed_lines = []
in_app_context = False
app_context_indent = 0
add_indent = False

for i, line in enumerate(lines):
    # Detect start of app_context block
    if 'with app.app_context():' in line:
        in_app_context = True
        app_context_indent = len(line) - len(line.lstrip())
        fixed_lines.append(line)
        continue
    
    # Detect the try: statement right after app_context
    if in_app_context and not add_indent and 'try:' in line.strip():
        add_indent = True
        fixed_lines.append(line)
        continue
    
    # Add indentation to lines after "try:" until we hit the outer except
    if add_indent:
        current_indent = len(line) - len(line.lstrip())
        
        # Check if this is the outer except block (same or less indent than try)
        if line.strip().startswith('except Exception as e:') and current_indent <= app_context_indent + 4:
            # This is the outer except, add one level of indent
            fixed_lines.append('    ' * (app_context_indent // 4 + 2) + line.lstrip())
            add_indent = False
            in_app_context = False
            continue
        
        # Add indent to all lines in try block
        if line.strip():  # Non-empty line
            fixed_lines.append('    ' + line)
        else:
            fixed_lines.append(line)
    else:
        fixed_lines.append(line)

# Write back
with open('src/workers/manual_tasks.py', 'w', encoding='utf-8') as f:
    f.writelines(fixed_lines)

print("✅ Indentation fixed!")
