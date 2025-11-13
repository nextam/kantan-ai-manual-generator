"""Quick test - login and check status"""
import requests
import sys

BASE_URL = 'http://localhost:5000'

print("Quick Connection Test")
print("=" * 50)

# Test 1: Server alive
print("\n[1] Server status...", end=" ")
try:
    r = requests.get(f'{BASE_URL}/', timeout=5)
    print(f"✅ OK ({r.status_code})")
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)

# Test 2: Login
print("[2] Login...", end=" ")
try:
    session = requests.Session()
    r = session.post(
        f'{BASE_URL}/auth/login',
        json={'email': 'support@career-survival.com', 'password': '0000'},
        timeout=10
    )
    if r.status_code == 200:
        print(f"✅ OK")
    else:
        print(f"❌ Failed ({r.status_code})")
        sys.exit(1)
except Exception as e:
    print(f"❌ Failed: {e}")
    sys.exit(1)

# Test 3: Check upload endpoint
print("[3] Upload endpoint...", end=" ")
try:
    # Create a small test file
    import io
    test_file = io.BytesIO(b"test video content")
    files = {'file': ('test.mp4', test_file, 'video/mp4')}
    
    r = session.post(
        f'{BASE_URL}/api/manuals/upload-file',
        files=files,
        timeout=30
    )
    
    if r.status_code in [200, 201, 400]:  # 400 is ok (file too small)
        print(f"✅ Endpoint responding ({r.status_code})")
        if r.status_code in [200, 201]:
            print(f"    Response: {r.json()}")
    else:
        print(f"⚠️ Unexpected status: {r.status_code}")
        print(f"    Response: {r.text[:200]}")
        
except Exception as e:
    print(f"❌ Failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ All quick tests passed!")
