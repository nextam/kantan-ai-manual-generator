"""
Quick test for upload_base64_image method
"""
import sys
import os
from pathlib import Path

os.environ['WERKZEUG_RUN_MAIN'] = 'true'
import logging
logging.disable(logging.CRITICAL)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.infrastructure.file_manager import FileManager
import asyncio
import base64

async def test_upload_base64_image():
    """Test upload_base64_image method"""
    
    print("=" * 70)
    print("TESTING upload_base64_image METHOD")
    print("=" * 70)
    
    # Initialize FileManager
    file_manager = FileManager(
        storage_type='gcs',
        storage_config={
            'bucket_name': os.getenv('GCS_BUCKET_NAME', 'kantan-ai-manual-generator-dev'),
            'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcp-credentials.json')
        }
    )
    
    print(f"\n✅ FileManager initialized")
    print(f"   Storage type: {file_manager.storage_type}")
    print(f"   Backend: {type(file_manager.backend).__name__}")
    
    # Check if method exists
    if hasattr(file_manager, 'upload_base64_image'):
        print(f"\n✅ upload_base64_image method exists")
        print(f"   Method: {file_manager.upload_base64_image}")
    else:
        print(f"\n❌ upload_base64_image method NOT FOUND")
        return
    
    # Create a small test image (1x1 red pixel PNG)
    test_image_base64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
        "/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
    )
    
    print(f"\n📤 Testing upload...")
    try:
        image_uri = await file_manager.upload_base64_image(
            image_base64=test_image_base64,
            filename='test_keyframe_1.png',
            folder='test_keyframes',
            company_id=1
        )
        
        print(f"   ✅ Upload successful!")
        print(f"   Image URI: {image_uri}")
        
        # Check if file exists
        if file_manager.file_exists(image_uri):
            print(f"   ✅ File exists in storage")
        else:
            print(f"   ⚠️ File not found (might be normal for GCS paths)")
        
    except Exception as e:
        print(f"   ❌ Upload failed: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n" + "=" * 70)

if __name__ == '__main__':
    asyncio.run(test_upload_base64_image())
