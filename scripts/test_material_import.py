import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

print("Testing material_routes import...")

try:
    from src.api.material_routes import material_bp
    print(f"✅ Import successful")
    print(f"   Blueprint name: {material_bp.name}")
    print(f"   URL prefix: {material_bp.url_prefix}")
    print(f"   Number of routes: {len(list(material_bp.deferred_functions))}")
    
    # List all routes
    print("\n   Routes:")
    for func in material_bp.deferred_functions:
        print(f"     - {func}")
    
except Exception as e:
    print(f"❌ Import failed: {e}")
    import traceback
    traceback.print_exc()
