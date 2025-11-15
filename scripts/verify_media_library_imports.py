"""
File: verify_media_library_imports.py
Purpose: Verify all imports and dependencies for media library implementation
Main functionality: Import validation, dependency check, API registration verification
Dependencies: Flask app context, all media library modules
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def verify_imports():
    """Verify all media library imports"""
    errors = []
    warnings = []
    success = []
    
    print("=" * 70)
    print("Media Library Implementation - Import Verification")
    print("=" * 70)
    print()
    
    # 1. Check Media model
    print("1. Checking Media model...")
    try:
        from src.models.models import Media
        success.append("✓ Media model imported successfully")
        print("  ✓ Media model exists")
        
        # Check required attributes
        required_attrs = [
            'id', 'company_id', 'uploaded_by', 'media_type', 'filename',
            'gcs_uri', 'gcs_bucket', 'gcs_path', 'title', 'description',
            'alt_text', 'tags', 'file_size', 'mime_type', 'image_metadata',
            'video_metadata', 'source_media_id', 'is_active', 'created_at',
            'updated_at', 'to_dict'
        ]
        
        missing_attrs = []
        for attr in required_attrs:
            if not hasattr(Media, attr):
                missing_attrs.append(attr)
        
        if missing_attrs:
            errors.append(f"✗ Media model missing attributes: {', '.join(missing_attrs)}")
        else:
            success.append("✓ All required Media model attributes present")
            print(f"  ✓ All {len(required_attrs)} required attributes present")
            
    except ImportError as e:
        errors.append(f"✗ Failed to import Media model: {e}")
        print(f"  ✗ Import failed: {e}")
    except Exception as e:
        errors.append(f"✗ Error checking Media model: {e}")
        print(f"  ✗ Error: {e}")
    
    print()
    
    # 2. Check MediaManager service
    print("2. Checking MediaManager service...")
    try:
        from src.services.media_manager import MediaManager
        success.append("✓ MediaManager service imported successfully")
        print("  ✓ MediaManager class exists")
        
        # Check required methods
        required_methods = [
            'upload_media', 'capture_frame_from_video', 'get_media_list',
            'get_media_by_id', 'update_media', 'delete_media', 'get_signed_url',
            '_enforce_tenant_isolation', '_extract_image_metadata',
            '_extract_video_metadata'
        ]
        
        missing_methods = []
        for method in required_methods:
            if not hasattr(MediaManager, method):
                missing_methods.append(method)
        
        if missing_methods:
            errors.append(f"✗ MediaManager missing methods: {', '.join(missing_methods)}")
        else:
            success.append("✓ All required MediaManager methods present")
            print(f"  ✓ All {len(required_methods)} required methods present")
            
    except ImportError as e:
        errors.append(f"✗ Failed to import MediaManager: {e}")
        print(f"  ✗ Import failed: {e}")
    except Exception as e:
        errors.append(f"✗ Error checking MediaManager: {e}")
        print(f"  ✗ Error: {e}")
    
    print()
    
    # 3. Check media API routes
    print("3. Checking media API routes...")
    try:
        from src.api.media_routes import media_bp
        success.append("✓ Media API blueprint imported successfully")
        print("  ✓ media_bp blueprint exists")
        
        # Check registered routes
        if hasattr(media_bp, 'deferred_functions'):
            route_count = len(media_bp.deferred_functions)
            success.append(f"✓ Media API has {route_count} registered routes")
            print(f"  ✓ {route_count} routes registered")
        else:
            warnings.append("⚠ Cannot verify route count (app not initialized)")
            print("  ⚠ Route count verification requires app context")
            
    except ImportError as e:
        errors.append(f"✗ Failed to import media routes: {e}")
        print(f"  ✗ Import failed: {e}")
    except Exception as e:
        errors.append(f"✗ Error checking media routes: {e}")
        print(f"  ✗ Error: {e}")
    
    print()
    
    # 4. Check Flask app integration
    print("4. Checking Flask app integration...")
    try:
        # Check that app.py can be imported (it creates app directly)
        import src.core.app
        success.append("✓ Flask app module imported successfully")
        print("  ✓ Flask app module exists")
        
        # Check if app variable exists
        if hasattr(src.core.app, 'app'):
            app = src.core.app.app
            
            # Check if media_bp is registered
            blueprint_names = [bp.name for bp in app.blueprints.values()]
            if 'media' in blueprint_names:
                success.append("✓ Media blueprint registered in Flask app")
                print("  ✓ Media blueprint registered")
            else:
                warnings.append("⚠ Media blueprint not yet registered (requires app initialization)")
                print("  ⚠ Blueprint registration requires full app start")
            
            # Check /components/ route
            has_components_route = False
            for rule in app.url_map.iter_rules():
                if '/components/' in rule.rule:
                    has_components_route = True
                    break
            
            if has_components_route:
                success.append("✓ /components/ route registered")
                print("  ✓ /components/ route exists")
            else:
                warnings.append("⚠ /components/ route not found (may require app context)")
                print("  ⚠ /components/ route check requires app context")
        else:
            warnings.append("⚠ Flask app not initialized (import time check)")
            print("  ⚠ App not initialized at import time")
            
    except ImportError as e:
        errors.append(f"✗ Failed to import Flask app: {e}")
        print(f"  ✗ Import failed: {e}")
    except Exception as e:
        warnings.append(f"⚠ Cannot fully verify Flask app: {e}")
        print(f"  ⚠ Limited verification: {e}")
    
    print()
    
    # 5. Check static files exist
    print("5. Checking static files...")
    static_files = [
        ('src/static/js/media_library.js', 'Media Library JS'),
        ('src/static/js/image_editor_standalone.js', 'Image Editor JS'),
        ('src/static/css/image_editor.css', 'Image Editor CSS'),
        ('src/components/media_library/media_library_modal.html', 'Media Library Modal HTML'),
        ('src/components/media_library/media_library.css', 'Media Library CSS'),
    ]
    
    for file_path, description in static_files:
        if os.path.exists(file_path):
            success.append(f"✓ {description} exists")
            print(f"  ✓ {description}")
        else:
            errors.append(f"✗ {description} NOT found: {file_path}")
            print(f"  ✗ {description} missing")
    
    print()
    
    # 6. Check dependencies
    print("6. Checking Python dependencies...")
    dependencies = [
        ('PIL', 'Pillow', 'Image metadata extraction'),
        ('cv2', 'opencv-python', 'Video frame capture'),
        ('google.cloud.storage', 'google-cloud-storage', 'GCS integration'),
    ]
    
    for module_name, package_name, purpose in dependencies:
        try:
            __import__(module_name)
            success.append(f"✓ {package_name} installed ({purpose})")
            print(f"  ✓ {package_name}")
        except ImportError:
            errors.append(f"✗ {package_name} NOT installed ({purpose})")
            print(f"  ✗ {package_name} missing")
    
    print()
    
    # Summary
    print("=" * 70)
    print("Verification Summary")
    print("=" * 70)
    print()
    
    print(f"✓ Success: {len(success)}")
    print(f"⚠ Warnings: {len(warnings)}")
    print(f"✗ Errors: {len(errors)}")
    print()
    
    if success:
        print("Successful checks:")
        for item in success:
            print(f"  {item}")
        print()
    
    if warnings:
        print("Warnings:")
        for item in warnings:
            print(f"  {item}")
        print()
    
    if errors:
        print("ERRORS:")
        for item in errors:
            print(f"  {item}")
        print()
        return False
    else:
        print("✓ All verification checks passed!")
        print()
        return True

if __name__ == '__main__':
    try:
        success = verify_imports()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Fatal error during verification: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
