import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.core.app import app

print("\nAll registered routes:")
print("=" * 80)

routes = []
for rule in app.url_map.iter_rules():
    routes.append({
        'endpoint': rule.endpoint,
        'methods': ','.join(sorted(rule.methods - {'OPTIONS', 'HEAD'})),
        'path': str(rule)
    })

# Filter and sort
routes = [r for r in routes if '/api/' in r['path'] or '/auth/' in r['path']]
routes.sort(key=lambda x: x['path'])

for route in routes:
    print(f"{route['methods']:15} {route['path']:50} -> {route['endpoint']}")

print("=" * 80)
print(f"\nTotal API routes: {len(routes)}")
