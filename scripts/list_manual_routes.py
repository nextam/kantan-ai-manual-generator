"""
List all registered routes in Flask app
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app

with app.app_context():
    print("=== Registered Routes ===\n")
    
    # Filter for manual-related routes
    manual_routes = []
    
    for rule in app.url_map.iter_rules():
        if 'manual' in rule.rule.lower():
            manual_routes.append({
                'endpoint': rule.endpoint,
                'methods': ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'})),
                'path': rule.rule
            })
    
    # Sort by path
    manual_routes.sort(key=lambda x: x['path'])
    
    print(f"Found {len(manual_routes)} manual-related routes:\n")
    
    for route in manual_routes:
        print(f"{route['methods']:20} {route['path']:50} -> {route['endpoint']}")
    
    # Check for upload-file specifically
    print("\n=== Checking for /api/manuals/upload-file ===")
    upload_found = any('/upload-file' in r['path'] for r in manual_routes)
    if upload_found:
        print("✅ /api/manuals/upload-file is registered")
    else:
        print("❌ /api/manuals/upload-file is NOT registered")
        print("\nAll /api/manuals routes:")
        for route in manual_routes:
            if route['path'].startswith('/api/manuals'):
                print(f"  {route['methods']:15} {route['path']}")
