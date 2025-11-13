"""
Test manual generation with actual video file
"""
import requests
import json
import time
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_URL = 'http://localhost:5000'
VIDEO_PATH = r"G:\共有ドライブ\CareerSurvival-all\customer\中部電力様\オカタ産業様\動画_オカタ産業様_20250620\検証用動画\0222_ビス打ち_若手_固定カメラ_IMG_0005.MOV"

print("="*80)
print("MANUAL GENERATION TEST")
print("="*80)

# Step 1: Login
print("\n[1/4] Logging in...")
session = requests.Session()
login_data = {
    'email': 'support@career-survival.com',
    'password': '0000'
}
response = session.post(f'{BASE_URL}/auth/login', json=login_data)
if response.status_code != 200:
    print(f"❌ Login failed: {response.status_code}")
    print(response.text)
    exit(1)
print("✅ Login successful")

# Step 2: Upload video
print("\n[2/4] Uploading video...")
print(f"   File: {VIDEO_PATH}")

try:
    with open(VIDEO_PATH, 'rb') as video_file:
        files = {'file': video_file}
        response = session.post(
            f'{BASE_URL}/api/manuals/upload-file', 
            files=files,
            timeout=300  # 5 minutes timeout for upload
        )
except requests.exceptions.Timeout:
    print("❌ Upload timed out after 300 seconds")
    exit(1)
except Exception as e:
    print(f"❌ Upload error: {str(e)}")
    exit(1)

if response.status_code != 200:
    print(f"❌ Upload failed: {response.status_code}")
    print(response.text)
    exit(1)

upload_result = response.json()
print(f"✅ Upload successful")
print(f"   Video URI: {upload_result['uri']}")
print(f"   File size: {upload_result['file_size'] / 1024 / 1024:.2f} MB")

video_uri = upload_result['uri']

# Step 3: Generate manual
print("\n[3/4] Generating manual...")
manual_data = {
    'title': '検証テスト - ビス打ち作業',
    'video_uri': video_uri,
    'output_format': 'text_with_images',
    'use_rag': False,  # Disable RAG for initial test
    'template_ids': [3]  # Use template ID 3
}

try:
    response = session.post(
        f'{BASE_URL}/api/manuals/generate', 
        json=manual_data,
        timeout=60  # 60 seconds timeout for generation request
    )
except requests.exceptions.Timeout:
    print("❌ Generation request timed out after 60 seconds")
    exit(1)
except Exception as e:
    print(f"❌ Generation request error: {str(e)}")
    exit(1)

if response.status_code not in [200, 201]:
    print(f"❌ Generation request failed: {response.status_code}")
    print(response.text)
    exit(1)

generation_result = response.json()
print(f"✅ Generation started")
print(f"   Manual ID: {generation_result['manuals'][0]['id']}")
print(f"   Job ID: {generation_result['manuals'][0]['job_id']}")
print(f"   Status: {generation_result['manuals'][0]['status']}")

manual_id = generation_result['manuals'][0]['id']
job_id = generation_result['manuals'][0]['job_id']

# Step 4: Monitor progress
print("\n[4/4] Monitoring generation progress...")
max_wait = 600  # 10 minutes
start_time = time.time()
last_progress = -1

while True:
    elapsed = time.time() - start_time
    if elapsed > max_wait:
        print(f"\n⏱️  Timeout after {max_wait} seconds")
        break
    
    # Check manual status
    response = session.get(f'{BASE_URL}/api/manuals/{manual_id}/status')
    
    if response.status_code != 200:
        print(f"\n❌ Status check failed: {response.status_code}")
        break
    
    status_data = response.json()
    
    if status_data.get('progress', 0) != last_progress:
        last_progress = status_data.get('progress', 0)
        print(f"   Progress: {last_progress}% - {status_data.get('current_step', 'Processing...')}")
    
    if status_data.get('status') == 'completed':
        print(f"\n✅ Manual generation completed!")
        print(f"   Time taken: {elapsed:.1f} seconds")
        
        # Get manual details
        response = session.get(f'{BASE_URL}/api/manuals/{manual_id}')
        if response.status_code == 200:
            manual = response.json()
            print(f"\n📖 Manual Details:")
            print(f"   Title: {manual.get('title')}")
            print(f"   Format: {manual.get('output_format')}")
            if manual.get('content'):
                content_preview = manual['content'][:200]
                print(f"   Content preview: {content_preview}...")
        break
    
    elif status_data.get('status') == 'failed':
        print(f"\n❌ Manual generation failed!")
        print(f"   Error: {status_data.get('error_message', 'Unknown error')}")
        break
    
    time.sleep(3)  # Check every 3 seconds

print("\n" + "="*80)
print("TEST COMPLETED")
print("="*80)
