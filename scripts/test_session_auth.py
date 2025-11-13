"""
Test session authentication for API endpoints
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = 'http://localhost:5000'

def test_login_and_api_call():
    """Test login and subsequent API call"""
    
    # Create a session to persist cookies
    session = requests.Session()
    
    print("=== Testing Session Authentication ===\n")
    
    # Step 1: Login
    print("[1] Attempting login...")
    login_data = {
        'email': 'support@career-survival.com',
        'password': '0000'
    }
    
    login_response = session.post(
        f'{BASE_URL}/auth/login',
        data=login_data,
        allow_redirects=False
    )
    
    print(f"Login Status: {login_response.status_code}")
    print(f"Login Headers: {dict(login_response.headers)}")
    
    # Check cookies
    print(f"\nCookies after login:")
    for cookie in session.cookies:
        print(f"  {cookie.name} = {cookie.value[:20]}...")
    
    if login_response.status_code not in [200, 302]:
        print(f"\n❌ Login failed: {login_response.text}")
        return False
    
    print("✅ Login successful\n")
    
    # Step 2: Call API endpoint
    print("[2] Calling /api/manuals/output-formats...")
    api_response = session.get(f'{BASE_URL}/api/manuals/output-formats')
    
    print(f"API Status: {api_response.status_code}")
    
    if api_response.status_code == 200:
        print("✅ API call successful")
        data = api_response.json()
        print(f"\nFormats count: {len(data.get('formats', []))}")
        for fmt in data.get('formats', [])[:2]:
            print(f"  - {fmt.get('name')} ({fmt.get('key')})")
        return True
    else:
        print(f"❌ API call failed: {api_response.status_code}")
        print(f"Response: {api_response.text}")
        return False

def test_direct_api_call():
    """Test direct API call without login (should fail)"""
    print("\n=== Testing Direct API Call (No Login) ===\n")
    
    response = requests.get(f'{BASE_URL}/api/manuals/output-formats')
    print(f"Status: {response.status_code}")
    
    if response.status_code == 401:
        print("✅ Correctly returned 401 (Unauthorized)")
    elif response.status_code == 403:
        print("⚠️ Returned 403 (Forbidden) - expected 401")
    else:
        print(f"❌ Unexpected status: {response.status_code}")
        print(f"Response: {response.text}")

if __name__ == '__main__':
    print("Starting authentication tests...\n")
    
    # Test direct API call (should fail)
    test_direct_api_call()
    
    # Test login + API call (should succeed)
    test_login_and_api_call()
    
    print("\n=== Test Complete ===")
