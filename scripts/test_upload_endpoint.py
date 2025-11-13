"""
Test video upload endpoint
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from io import BytesIO

BASE_URL = 'http://localhost:5000'

def test_upload_endpoint():
    """Test /api/manuals/upload-file endpoint"""
    
    # Create a session and login
    session = requests.Session()
    
    print("=== Testing Video Upload Endpoint ===\n")
    
    # Step 1: Login
    print("[1] Logging in...")
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
        return
    
    print("✅ Login successful\n")
    
    # Step 2: Create a dummy video file
    print("[2] Creating dummy video file...")
    dummy_video = BytesIO(b'\x00' * 1024)  # 1KB dummy file
    dummy_video.name = 'test_video.mp4'
    
    # Step 3: Upload video
    print("[3] Uploading video to /api/manuals/upload-file...")
    
    files = {'file': ('test_video.mp4', dummy_video, 'video/mp4')}
    
    upload_response = session.post(
        f'{BASE_URL}/api/manuals/upload-file',
        files=files
    )
    
    print(f"Status: {upload_response.status_code}")
    
    if upload_response.status_code == 200:
        print("✅ Upload successful")
        data = upload_response.json()
        print(f"\nResponse:")
        print(f"  GCS URI: {data.get('gcs_uri')}")
        print(f"  File name: {data.get('file_name')}")
        print(f"  File size: {data.get('file_size')} bytes")
    else:
        print(f"❌ Upload failed")
        print(f"Response: {upload_response.text}")

if __name__ == '__main__':
    test_upload_endpoint()
