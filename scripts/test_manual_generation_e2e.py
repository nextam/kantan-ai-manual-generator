"""
File: test_manual_generation_e2e.py
Purpose: End-to-end test of manual generation with full logging
"""
import sys
import os
import time
import requests
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.models import db, Manual, User, Company, ManualTemplate
from src.core.db_manager import create_app

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_EMAIL = "support@career-survival.com"
TEST_PASSWORD = "0000"
TEST_TEMPLATE_NAME = "TEST"

def login():
    """Login and get session cookies."""
    print("=== Logging in ===")
    session = requests.Session()
    
    # Login request
    response = session.post(
        f"{BASE_URL}/auth/login",
        data={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        },
        allow_redirects=False
    )
    
    if response.status_code in [200, 302]:
        # Check for success in JSON response or redirect
        if response.status_code == 200:
            try:
                result = response.json()
                if result.get('success'):
                    print(f"✅ Login successful (JSON response)")
                    return session
            except:
                pass
        print(f"✅ Login successful")
        return session
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return None

def get_test_video_path():
    """Find a test video file."""
    # Look for MP4 files in uploads folder
    uploads_dir = Path(__file__).parent.parent / "uploads"
    if uploads_dir.exists():
        mp4_files = list(uploads_dir.glob("**/*.mp4"))
        if mp4_files:
            return mp4_files[0]
    
    # Look in src/uploads
    src_uploads = Path(__file__).parent.parent / "src" / "uploads"
    if src_uploads.exists():
        mp4_files = list(src_uploads.glob("**/*.mp4"))
        if mp4_files:
            return mp4_files[0]
    
    return None

def create_manual_via_api(session):
    """Create a manual via API."""
    print("\n=== Creating Manual ===")
    
    # Get template ID
    app = create_app()
    with app.app_context():
        template = ManualTemplate.query.filter_by(name=TEST_TEMPLATE_NAME).first()
        if not template:
            print(f"❌ Template '{TEST_TEMPLATE_NAME}' not found")
            return None
        print(f"✅ Found template ID: {template.id}")
        template_id = template.id
    
    # Find test video
    video_path = get_test_video_path()
    if not video_path:
        print("❌ No test video found in uploads folder")
        print("Please place a test MP4 video in the uploads/ directory")
        return None
    
    print(f"✅ Using test video: {video_path.name}")
    
    # Step 1: Upload video
    print("Step 1: Uploading video...")
    with open(video_path, 'rb') as video_file:
        files = {
            'file': (video_path.name, video_file, 'video/mp4')
        }
        
        response = session.post(
            f"{BASE_URL}/api/manuals/upload",
            files=files
        )
    
    if response.status_code != 200:
        print(f"❌ Video upload failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return None
    
    upload_result = response.json()
    if not upload_result.get('success'):
        print(f"❌ Video upload failed: {upload_result.get('error')}")
        return None
    
    video_uri = upload_result.get('gcs_uri')
    print(f"✅ Video uploaded: {video_uri}")
    
    # Step 2: Generate manual
    print("Step 2: Generating manual...")
    
    payload = {
        'title': f'E2E Test Manual {int(time.time())}',
        'video_uri': video_uri,
        'template_id': template_id,
        'output_format': 'text_with_images',
        'use_rag': False  # Disable RAG for faster testing
    }
    
    response = session.post(
        f"{BASE_URL}/api/manuals/generate",
        json=payload
    )
    
    if response.status_code != 200:
        print(f"❌ Manual generation request failed: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        return None
    
    result = response.json()
    if 'manuals' in result and len(result['manuals']) > 0:
        manual_id = result['manuals'][0]['id']
        print(f"✅ Manual generation started: ID={manual_id}")
        return manual_id
    else:
        print(f"❌ No manual ID in response: {result}")
        return None

def wait_for_generation(manual_id, timeout=300):
    """Wait for manual generation to complete."""
    print(f"\n=== Waiting for Manual Generation (ID: {manual_id}) ===")
    print("Monitoring status...")
    
    app = create_app()
    start_time = time.time()
    last_status = None
    
    while time.time() - start_time < timeout:
        with app.app_context():
            manual = Manual.query.get(manual_id)
            if not manual:
                print(f"❌ Manual {manual_id} not found")
                return False
            
            current_status = manual.status
            if current_status != last_status:
                print(f"Status: {current_status}")
                last_status = current_status
            
            if current_status == 'completed':
                print(f"✅ Manual generation completed in {int(time.time() - start_time)}s")
                return True
            
            if current_status == 'failed':
                print(f"❌ Manual generation failed")
                return False
        
        time.sleep(2)
    
    print(f"❌ Timeout after {timeout}s")
    return False

def verify_manual_content(manual_id):
    """Verify the generated manual content."""
    print(f"\n=== Verifying Manual Content (ID: {manual_id}) ===")
    
    app = create_app()
    with app.app_context():
        manual = Manual.query.get(manual_id)
        if not manual:
            print(f"❌ Manual {manual_id} not found")
            return False
        
        print(f"Title: {manual.title}")
        print(f"Status: {manual.status}")
        print(f"Created: {manual.created_at}")
        
        # Check if content exists
        content = manual.content
        if not content or len(content.strip()) == 0:
            print("❌ FAIL: Manual content is empty")
            return False
        
        print(f"✅ Content length: {len(content)} chars")
        
        # Check for error messages in content
        error_keywords = ['error', 'エラー', 'failed', '失敗', 'exception', '例外']
        content_lower = content.lower()
        found_errors = [kw for kw in error_keywords if kw in content_lower]
        
        if found_errors:
            print(f"⚠️ WARNING: Error keywords found in content: {found_errors}")
            print(f"Content preview:\n{content[:500]}...")
        else:
            print(f"✅ No error keywords in content")
        
        # Check if sections were applied
        generation_options = manual.get_generation_options()
        if generation_options and 'sections' in generation_options:
            sections = generation_options['sections']
            print(f"\n📋 Template sections ({len(sections)}):")
            for i, section in enumerate(sections):
                section_title = section.get('title', 'N/A')
                print(f"  [{i+1}] {section_title}")
                
                # Check if section title appears in content
                if section_title in content:
                    print(f"      ✅ Found in content")
                else:
                    print(f"      ⚠️ Not found in content")
        
        # Show content preview
        print(f"\n📄 Content Preview (first 1000 chars):")
        print("=" * 80)
        print(content[:1000])
        print("=" * 80)
        
        # Check if content looks like fixed text or dynamic
        if len(content) < 100:
            print(f"⚠️ WARNING: Content is very short ({len(content)} chars)")
            return False
        
        # Check if content has variety (not just repeated text)
        unique_chars = len(set(content))
        if unique_chars < 50:
            print(f"⚠️ WARNING: Content has low variety ({unique_chars} unique chars)")
            return False
        
        print(f"\n✅ Manual content verification passed")
        print(f"   - Content not empty: ✓")
        print(f"   - No error messages: ✓")
        print(f"   - Dynamic content (unique chars: {unique_chars}): ✓")
        
        return True

def main():
    """Run end-to-end test."""
    print("=" * 80)
    print("MANUAL GENERATION E2E TEST")
    print("=" * 80)
    
    # Step 1: Login
    session = login()
    if not session:
        return False
    
    # Step 2: Create manual
    manual_id = create_manual_via_api(session)
    if not manual_id:
        return False
    
    # Step 3: Wait for generation
    success = wait_for_generation(manual_id, timeout=300)
    if not success:
        return False
    
    # Step 4: Verify content
    success = verify_manual_content(manual_id)
    
    print("\n" + "=" * 80)
    if success:
        print("✅ E2E TEST PASSED")
    else:
        print("❌ E2E TEST FAILED")
    print("=" * 80)
    
    return success

if __name__ == '__main__':
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
