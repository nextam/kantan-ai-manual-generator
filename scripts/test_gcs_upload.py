"""
Test video upload to GCS with company_id-based folder structure
"""

import os
import sys
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Test account credentials
TEST_COMPANY_ID = 'career-survival'
TEST_USER_EMAIL = 'support@career-survival.com'
TEST_PASSWORD = '0000'

BASE_URL = 'http://localhost:5000'

print("=== Video Upload Test with GCS ===\n")

# Step 1: Login
print("Step 1: Logging in...")
login_response = requests.post(
    f'{BASE_URL}/auth/login',
    json={
        'company_id': TEST_COMPANY_ID,
        'email': TEST_USER_EMAIL,
        'password': TEST_PASSWORD
    }
)

if login_response.status_code != 200:
    print(f"❌ Login failed: {login_response.status_code}")
    print(f"Response: {login_response.text}")
    sys.exit(1)

print("✅ Login successful")
session_cookies = login_response.cookies

# Step 2: Find a test video file
print("\nStep 2: Finding test video file...")
test_video_path = None

# Search for video files in uploads directory
uploads_dir = Path('uploads')
if uploads_dir.exists():
    for video_ext in ['mp4', 'mov', 'avi']:
        video_files = list(uploads_dir.rglob(f'*.{video_ext}'))
        if video_files:
            test_video_path = video_files[0]
            break

if not test_video_path or not test_video_path.exists():
    print("❌ No test video found in uploads directory")
    print("Please ensure there is at least one video file in uploads/")
    sys.exit(1)

print(f"✅ Using test video: {test_video_path}")
print(f"   File size: {test_video_path.stat().st_size / (1024*1024):.2f} MB")

# Step 3: Upload video
print("\nStep 3: Uploading video to GCS...")
with open(test_video_path, 'rb') as f:
    files = {'file': (test_video_path.name, f, 'video/mp4')}
    upload_response = requests.post(
        f'{BASE_URL}/api/manuals/upload-file',
        files=files,
        cookies=session_cookies
    )

if upload_response.status_code != 200:
    print(f"❌ Upload failed: {upload_response.status_code}")
    print(f"Response: {upload_response.text}")
    sys.exit(1)

upload_result = upload_response.json()
print("✅ Upload successful!")
print(f"\n=== Upload Result ===")
print(f"GCS URI: {upload_result.get('gcs_uri')}")
print(f"File name: {upload_result.get('file_name')}")
print(f"File size: {upload_result.get('file_size', 0) / (1024*1024):.2f} MB")
print(f"Storage type: {upload_result.get('storage_type')}")

# Verify gs:// URI format
gcs_uri = upload_result.get('gcs_uri', '')
if gcs_uri.startswith('gs://'):
    print(f"\n✅ GCS URI format is correct: {gcs_uri}")
    
    # Check if it includes company_id folder
    if 'company_' in gcs_uri:
        print("✅ Company-based folder structure is applied")
    else:
        print("⚠️ Warning: Company-based folder structure may not be applied")
else:
    print(f"\n❌ ERROR: Not a GCS URI format: {gcs_uri}")
    print("Expected format: gs://bucket/company_X/videos/...")

print("\n=== Test Complete ===")
