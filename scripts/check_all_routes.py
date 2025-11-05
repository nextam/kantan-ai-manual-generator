"""
File: check_all_routes.py
Purpose: List all registered Flask routes including UI routes
Main functionality: Display all routes to verify UI blueprint registration
Dependencies: Flask app
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.app import app

print("\nAll registered routes:")
print("=" * 100)

routes = []
for rule in app.url_map.iter_rules():
    routes.append({
        'endpoint': rule.endpoint,
        'methods': ','.join(sorted(rule.methods - {'OPTIONS', 'HEAD'})),
        'path': str(rule)
    })

# Sort by path
routes.sort(key=lambda x: x['path'])

for route in routes:
    print(f"{route['methods']:15} {route['path']:60} -> {route['endpoint']}")

print("=" * 100)
print(f"\nTotal routes: {len(routes)}")

# Check for UI routes specifically
ui_routes = [r for r in routes if r['path'].startswith('/super-admin/') or r['path'].startswith('/company/') or r['path'] in ['/materials', '/jobs']]
print(f"UI routes found: {len(ui_routes)}")
if ui_routes:
    print("\nUI Routes:")
    for r in ui_routes:
        print(f"  {r['path']} -> {r['endpoint']}")
