import requests

try:
    # Test login page
    response = requests.get('http://localhost:5000/login', timeout=5)
    print(f"Login Page Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print("\n✅ Login page is accessible!")
        
        # Try logging in with test account
        login_data = {
            'company_code': 'career-survival',
            'password': '0000',
            'username': 'support@career-survival.com'
        }
        
        session = requests.Session()
        login_response = session.post('http://localhost:5000/login', data=login_data, timeout=5)
        
        print(f"\nLogin POST Status Code: {login_response.status_code}")
        
        if login_response.status_code == 200:
            print("✅ Login successful!")
            print(f"Response URL: {login_response.url}")
        elif login_response.status_code == 302:
            print(f"✅ Login redirect: {login_response.headers.get('Location')}")
        else:
            print(f"Login response preview:")
            print(login_response.text[:500])
    else:
        print(f"Response: {response.text[:500]}")
        
except requests.exceptions.ConnectionError:
    print("ERROR: Cannot connect to server")
except requests.exceptions.Timeout:
    print("ERROR: Request timeout")
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
