"""
Test import of manual_routes
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from src.api.manual_routes import manual_bp
    print("✅ manual_bp import successful")
    
    # List routes
    print(f"\nRoutes in manual_bp:")
    for rule in manual_bp.deferred_functions:
        print(f"  - Deferred function: {rule}")
        
except ImportError as e:
    print(f"❌ Import error: {e}")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
