"""
File: test_email_login.py
Purpose: Test email-based login authentication
Main functionality: Verify new email + password authentication works
Dependencies: requests, Flask app
"""
import requests
import json

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_EMAIL = "support@career-survival.com"
TEST_PASSWORD = "0000"

def test_api_login():
    """Test API login endpoint with email + password"""
    print("=" * 60)
    print("Testing API Login (/auth/login)")
    print("=" * 60)
    
    url = f"{BASE_URL}/auth/login"
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        response = requests.post(url, json=payload)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")
        
        if response.status_code == 200:
            print("\n✅ API Login successful!")
            return True
        else:
            print("\n❌ API Login failed!")
            return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def test_html_login():
    """Test HTML form login endpoint with email + password"""
    print("\n" + "=" * 60)
    print("Testing HTML Form Login (/login)")
    print("=" * 60)
    
    url = f"{BASE_URL}/login"
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    print(f"\nRequest URL: {url}")
    print(f"Request payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Use session to maintain cookies
        session = requests.Session()
        response = session.post(url, data=payload, allow_redirects=False)
        
        print(f"\nResponse Status: {response.status_code}")
        
        # Check for redirect (successful login redirects to dashboard)
        if response.status_code == 302:
            redirect_url = response.headers.get('Location', 'N/A')
            print(f"Redirect Location: {redirect_url}")
            print("\n✅ HTML Form Login successful! (Redirected)")
            return True
        elif response.status_code == 200:
            print(f"Response Body: {response.text[:500]}")
            print("\n❌ HTML Form Login failed! (No redirect)")
            return False
        else:
            print(f"Response Body: {response.text[:500]}")
            print("\n❌ HTML Form Login failed!")
            return False
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        return False

def main():
    print("\n🚀 Starting Email-Based Login Tests")
    print(f"Test Account: {TEST_EMAIL}")
    print(f"Test Password: {TEST_PASSWORD}")
    print(f"Server URL: {BASE_URL}")
    
    # Check if server is running
    try:
        response = requests.get(BASE_URL, timeout=3)
        print(f"\n✅ Server is running (Status: {response.status_code})")
    except:
        print(f"\n❌ Server is NOT running at {BASE_URL}")
        print("Please start the server first using VS Code task or run_local_gunicorn.bat")
        return
    
    # Run tests
    api_result = test_api_login()
    html_result = test_html_login()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"API Login (/auth/login): {'✅ PASS' if api_result else '❌ FAIL'}")
    print(f"HTML Form Login (/login): {'✅ PASS' if html_result else '❌ FAIL'}")
    
    if api_result and html_result:
        print("\n🎉 All tests passed! Email-based authentication is working!")
    else:
        print("\n⚠️ Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()
