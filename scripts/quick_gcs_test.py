"""
Quick test: Login and upload video to verify GCS integration
"""
import requests
import sys
from pathlib import Path

BASE_URL = 'http://localhost:5000'

print("1. Testing login...")
response = requests.post(
    f'{BASE_URL}/auth/login',
    json={
        'company_id': 'career-survival',
        'email': 'support@career-survival.com',
        'password': '0000'
    }
)

if response.status_code == 200:
    print("✅ Login successful")
    cookies = response.cookies
else:
    print(f"❌ Login failed: {response.status_code}")
    print(response.text)
    sys.exit(1)

print("\n2. Finding test video...")
video_path = None
for ext in ['mp4', 'mov', 'avi']:
    files = list(Path('uploads').rglob(f'*.{ext}'))
    if files:
        video_path = files[0]
        break

if not video_path:
    print("❌ No video found")
    sys.exit(1)

print(f"✅ Found: {video_path.name} ({video_path.stat().st_size / (1024*1024):.1f}MB)")

print("\n3. Uploading to GCS...")
with open(video_path, 'rb') as f:
    response = requests.post(
        f'{BASE_URL}/api/manuals/upload-file',
        files={'file': (video_path.name, f, 'video/mp4')},
        cookies=cookies,
        timeout=120
    )

if response.status_code == 200:
    result = response.json()
    gcs_uri = result.get('gcs_uri', '')
    print("✅ Upload successful")
    print(f"   URI: {gcs_uri}")
    print(f"   Storage: {result.get('storage_type')}")
    
    # Verify
    if 'kantan-ai-manual-generator-dev' in gcs_uri and 'company_1/videos/' in gcs_uri:
        print("✅ GCS integration working correctly!")
        print(f"\n🎉 Test passed! Ready to generate manual with: {gcs_uri}")
    else:
        print("❌ Unexpected GCS URI format")
else:
    print(f"❌ Upload failed: {response.status_code}")
    print(response.text[:500])
