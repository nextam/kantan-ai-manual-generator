import sys
sys.path.insert(0, '.')
from src.core.app import app

print('Registered blueprints:')
for bp_name, bp in app.blueprints.items():
    print(f'  - {bp_name}: {bp.url_prefix}')
