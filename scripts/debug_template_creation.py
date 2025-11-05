"""
File: debug_template_creation.py
Purpose: Debug template creation endpoint
Main functionality: Test template creation with verbose error output
Dependencies: requests
"""

import requests
import json

BASE_URL = "http://localhost:5000"

# Login as company admin
session = requests.Session()
login_data = {
    "company_code": "career-survival",
    "username": "support@career-survival.com",
    "password": "0000"
}

print("Step 1: Login as company admin")
response = session.post(f"{BASE_URL}/auth/login", json=login_data)
print(f"Login Status: {response.status_code}")
if response.status_code != 200:
    print(f"Login failed: {response.text}")
    exit(1)

print(f"Login Response: {json.dumps(response.json(), indent=2)}")

# Create template
print("\nStep 2: Create template")
template_data = {
    "name": f"Debug Template",
    "description": "Test template for debugging",
    "template_content": {
        "sections": [
            {"name": "Introduction", "prompt": "Generate intro"},
            {"name": "Steps", "prompt": "List steps"}
        ],
        "style": "simple",
        "language": "ja"
    },
    "is_default": False
}

print(f"Request Data: {json.dumps(template_data, indent=2, ensure_ascii=False)}")

response = session.post(
    f"{BASE_URL}/api/company/templates",
    json=template_data,
    headers={'Content-Type': 'application/json'}
)

print(f"\nResponse Status: {response.status_code}")
print(f"Response Headers: {dict(response.headers)}")
print(f"Response Body: {response.text}")

if response.status_code == 201:
    print("\n✅ Template created successfully!")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
else:
    print(f"\n❌ Template creation failed!")
    try:
        error_data = response.json()
        print(f"Error: {json.dumps(error_data, indent=2, ensure_ascii=False)}")
    except:
        print(f"Raw response: {response.text}")
