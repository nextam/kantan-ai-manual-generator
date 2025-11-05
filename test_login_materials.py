"""Test login API with correct credentials"""
import requests
import json

# ログインテスト
login_url = "http://localhost:5000/auth/login"
login_data = {
    "company_code": "career-survival",
    "username": "support@career-survival.com",
    "password": "0000"
}

print("Testing login API...")
print(f"URL: {login_url}")
print(f"Data: {json.dumps(login_data, indent=2)}")
print()

response = requests.post(login_url, json=login_data)

print(f"Status Code: {response.status_code}")
print(f"Response Headers:")
for key, value in response.headers.items():
    print(f"  {key}: {value}")
print()
print(f"Response Body:")
print(response.text)
print()

if response.status_code == 200:
    print("✅ Login successful!")
    
    # セッションを使って/api/materialsにアクセス
    session = requests.Session()
    session.cookies.update(response.cookies)
    
    materials_url = "http://localhost:5000/api/materials"
    print(f"\nTesting materials API with session...")
    print(f"URL: {materials_url}")
    
    materials_response = session.get(materials_url)
    print(f"Status Code: {materials_response.status_code}")
    print(f"Response: {materials_response.text[:500]}")
    
    if materials_response.status_code == 200:
        print("\n✅ Materials API accessible!")
    else:
        print(f"\n❌ Materials API returned {materials_response.status_code}")
else:
    print(f"❌ Login failed with status {response.status_code}")
