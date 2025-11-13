"""Test with real video file - with progress display"""
import requests
import time
import sys
from pathlib import Path

BASE_URL = 'http://localhost:5000'
VIDEO_PATH = r"G:\共有ドライブ\CareerSurvival-all\customer\中部電力様\オカタ産業様\動画_オカタ産業様_20250620\検証用動画\0222_ビス打ち_若手_固定カメラ_IMG_0005.MOV"

print("=" * 70)
print("REAL VIDEO TEST")
print("=" * 70)

# Check file
video_file = Path(VIDEO_PATH)
if not video_file.exists():
    print(f"❌ File not found: {VIDEO_PATH}")
    sys.exit(1)

file_size_mb = video_file.stat().st_size / (1024 * 1024)
print(f"\n📹 Video: {video_file.name}")
print(f"📊 Size: {file_size_mb:.2f} MB")

# Login
print("\n[1/3] Logging in...", end=" ", flush=True)
session = requests.Session()
try:
    r = session.post(
        f'{BASE_URL}/auth/login',
        json={'email': 'support@career-survival.com', 'password': '0000'},
        timeout=10
    )
    if r.status_code != 200:
        print(f"❌ Failed ({r.status_code})")
        sys.exit(1)
    print("✅")
except Exception as e:
    print(f"❌ {e}")
    sys.exit(1)

# Upload with timeout and progress
print(f"\n[2/3] Uploading {file_size_mb:.2f} MB...")
print("      (Timeout: 5 minutes)")

start_time = time.time()

try:
    with open(video_file, 'rb') as f:
        files = {'file': (video_file.name, f, 'video/quicktime')}
        
        print("      Sending request...", flush=True)
        r = session.post(
            f'{BASE_URL}/api/manuals/upload-file',
            files=files,
            timeout=300
        )
        
    elapsed = time.time() - start_time
    
    if r.status_code not in [200, 201]:
        print(f"      ❌ Failed ({r.status_code})")
        print(f"      Response: {r.text[:300]}")
        sys.exit(1)
    
    result = r.json()
    print(f"      ✅ Uploaded in {elapsed:.1f}s")
    print(f"      URI: {result['uri']}")
    
    video_uri = result['uri']
    
except requests.exceptions.Timeout:
    print(f"      ❌ Timeout after 300s")
    sys.exit(1)
except Exception as e:
    print(f"      ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Generate manual
print(f"\n[3/3] Starting manual generation...")

manual_data = {
    'title': 'テスト - ビス打ち作業',
    'video_uri': video_uri,
    'output_format': 'text_with_images',
    'use_rag': False,
    'template_ids': [3]
}

start_time = time.time()

try:
    print("      Sending request...", flush=True)
    r = session.post(
        f'{BASE_URL}/api/manuals/generate',
        json=manual_data,
        timeout=60
    )
    
    elapsed = time.time() - start_time
    
    if r.status_code not in [200, 201]:
        print(f"      ❌ Failed ({r.status_code})")
        print(f"      Response: {r.text[:300]}")
        sys.exit(1)
    
    result = r.json()
    print(f"      ✅ Started in {elapsed:.1f}s")
    
    if 'manuals' in result and len(result['manuals']) > 0:
        manual = result['manuals'][0]
        print(f"\n      📋 Manual ID: {manual['id']}")
        print(f"      🔧 Job ID: {manual['job_id']}")
        print(f"      📊 Status: {manual['status']}")
        print(f"\n      ℹ️ Background processing started")
        print(f"      Check UI or database for progress")
    else:
        print(f"      ⚠️ Unexpected response: {result}")
        
except requests.exceptions.Timeout:
    print(f"      ❌ Timeout after 60s")
    sys.exit(1)
except Exception as e:
    print(f"      ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 70)
print("✅ TEST COMPLETED SUCCESSFULLY")
print("=" * 70)
