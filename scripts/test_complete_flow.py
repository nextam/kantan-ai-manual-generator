"""
Test complete upload and generation flow
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from io import BytesIO

BASE_URL = 'http://localhost:5000'

def test_complete_flow():
    """Test complete manual generation flow"""
    
    session = requests.Session()
    
    print("=" * 80)
    print("TESTING COMPLETE MANUAL GENERATION FLOW")
    print("=" * 80)
    
    # Step 1: Login
    print("\n[1] Logging in...")
    login_response = session.post(
        f'{BASE_URL}/auth/login',
        data={
            'email': 'support@career-survival.com',
            'password': '0000'
        },
        allow_redirects=False
    )
    
    if login_response.status_code not in [200, 302]:
        print(f"❌ Login failed: {login_response.status_code}")
        return False
    
    print("✅ Login successful")
    
    # Step 2: Upload video
    print("\n[2] Uploading video...")
    dummy_video = BytesIO(b'\x00' * 1024 * 100)  # 100KB dummy file
    files = {'file': ('test_manual_video.mp4', dummy_video, 'video/mp4')}
    
    upload_response = session.post(
        f'{BASE_URL}/api/manuals/upload-file',
        files=files
    )
    
    print(f"Upload status: {upload_response.status_code}")
    
    if upload_response.status_code != 200:
        print(f"❌ Upload failed")
        print(f"Response: {upload_response.text}")
        return False
    
    upload_data = upload_response.json()
    print(f"✅ Upload successful")
    print(f"   GCS URI: {upload_data.get('gcs_uri')}")
    
    video_uri = upload_data.get('gcs_uri') or upload_data.get('uri')
    
    # Step 3: Generate manual
    print("\n[3] Generating manual...")
    
    generate_payload = {
        'title': 'Test Manual via API',
        'description': 'This is a test manual generated via API',
        'video_uri': video_uri,
        'output_format': 'text_with_images',
        'use_rag': False,  # Disable RAG for testing
        'custom_prompt': ''
    }
    
    print(f"Payload: {generate_payload}")
    
    generate_response = session.post(
        f'{BASE_URL}/api/manuals/generate',
        json=generate_payload
    )
    
    print(f"Generate status: {generate_response.status_code}")
    
    if generate_response.status_code not in [200, 201]:
        print(f"❌ Generate failed")
        print(f"Response: {generate_response.text}")
        return False
    
    generate_data = generate_response.json()
    print(f"✅ Generate successful")
    print(f"Response: {generate_data}")
    
    print("\n" + "=" * 80)
    print("FLOW TEST COMPLETED SUCCESSFULLY")
    print("=" * 80)
    return True

if __name__ == '__main__':
    success = test_complete_flow()
    sys.exit(0 if success else 1)
