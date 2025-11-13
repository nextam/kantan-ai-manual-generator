"""
Comprehensive route debugging script
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG)

with app.app_context():
    print("=" * 80)
    print("COMPREHENSIVE ROUTE ANALYSIS")
    print("=" * 80)
    
    # 1. Check all registered blueprints
    print("\n[1] REGISTERED BLUEPRINTS:")
    print("-" * 80)
    for blueprint_name, blueprint in app.blueprints.items():
        print(f"  - {blueprint_name:30} URL Prefix: {blueprint.url_prefix}")
    
    # 2. Find all routes containing 'upload'
    print("\n[2] ALL ROUTES CONTAINING 'upload':")
    print("-" * 80)
    upload_routes = []
    for rule in app.url_map.iter_rules():
        if 'upload' in rule.rule.lower():
            methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            upload_routes.append({
                'path': rule.rule,
                'methods': methods,
                'endpoint': rule.endpoint
            })
            print(f"  {methods:15} {rule.rule:60} -> {rule.endpoint}")
    
    if not upload_routes:
        print("  ❌ NO UPLOAD ROUTES FOUND!")
    
    # 3. Check specific paths
    print("\n[3] CHECKING SPECIFIC PATHS:")
    print("-" * 80)
    
    paths_to_check = [
        '/api/upload-file',
        '/api/manuals/upload-file',
        '/upload-file'
    ]
    
    for path in paths_to_check:
        matching = [r for r in app.url_map.iter_rules() if r.rule == path]
        if matching:
            print(f"  ✅ {path:40} EXISTS")
            for rule in matching:
                methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
                print(f"     Methods: {methods}, Endpoint: {rule.endpoint}")
        else:
            print(f"  ❌ {path:40} NOT FOUND")
    
    # 4. Check manual_api blueprint specifically
    print("\n[4] MANUAL_API BLUEPRINT ROUTES:")
    print("-" * 80)
    manual_routes = [r for r in app.url_map.iter_rules() if r.endpoint and r.endpoint.startswith('manual_api')]
    if manual_routes:
        for rule in manual_routes:
            methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            print(f"  {methods:15} {rule.rule:60} -> {rule.endpoint}")
    else:
        print("  ❌ NO MANUAL_API ROUTES FOUND!")
    
    # 5. Check if manual_bp is registered
    print("\n[5] MANUAL_BP REGISTRATION CHECK:")
    print("-" * 80)
    try:
        from src.api.manual_routes import manual_bp
        print(f"  ✅ manual_bp imported successfully")
        print(f"     Name: {manual_bp.name}")
        print(f"     URL Prefix: {manual_bp.url_prefix}")
        
        # Check deferred functions
        if hasattr(manual_bp, 'deferred_functions'):
            print(f"     Deferred functions: {len(manual_bp.deferred_functions)}")
    except Exception as e:
        print(f"  ❌ Failed to import manual_bp: {e}")
        import traceback
        traceback.print_exc()
    
    # 6. Total route count
    print("\n[6] SUMMARY:")
    print("-" * 80)
    total_routes = len(list(app.url_map.iter_rules()))
    print(f"  Total routes registered: {total_routes}")
    print(f"  Upload-related routes: {len(upload_routes)}")
    print(f"  Manual API routes: {len(manual_routes)}")
    
    print("\n" + "=" * 80)
