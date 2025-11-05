"""
File: test_flask_routes.py
Purpose: Test Flask route registration
Main functionality: Display all registered routes
Dependencies: Flask app
"""

import sys
sys.path.insert(0, 'c:\\Users\\nekus\\github\\kantan-ai-manual-generator')

from src.core.app import app

print("=== All Registered Flask Routes ===\n")

routes = []
for rule in app.url_map.iter_rules():
    routes.append({
        'endpoint': rule.endpoint,
        'methods': ','.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
        'path': str(rule)
    })

# Filter for admin routes
admin_routes = [r for r in routes if '/admin/' in r['path']]
test_routes = [r for r in routes if '/test/' in r['path']]

print(f"Total routes: {len(routes)}")
print(f"Admin routes: {len(admin_routes)}")
print(f"Test routes: {len(test_routes)}\n")

print("=== Admin Routes ===")
for route in sorted(admin_routes, key=lambda x: x['path']):
    print(f"{route['methods']:20s} {route['path']}")

print("\n=== Test Routes ===")
for route in sorted(test_routes, key=lambda x: x['path']):
    print(f"{route['methods']:20s} {route['path']}")
