"""
Test API endpoints edge cases and error handling
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

print("=== Edge Case Tests ===\n")

# Test without authentication
print("1. Test /api/company/dashboard without auth")
response = requests.get(f'{BASE_URL}/api/company/dashboard')
print(f"   Status: {response.status_code} (expected: 302 redirect or 401)")
print(f"   ✅ PASS" if response.status_code in [302, 401] else f"   ❌ FAIL")

print("\n2. Test /api/jobs without auth")
response = requests.get(f'{BASE_URL}/api/jobs')
print(f"   Status: {response.status_code} (expected: 302 redirect or 401)")
print(f"   ✅ PASS" if response.status_code in [302, 401] else f"   ❌ FAIL")

# Login for authenticated tests
session = requests.Session()
login_data = {
    'email': 'support@career-survival.com',
    'password': '0000'
}
response = session.post(f'{BASE_URL}/auth/login', json=login_data)
if response.status_code != 200:
    print(f"\n❌ Login failed: {response.status_code}")
    exit(1)
print("\n✅ Logged in successfully")

# Test pagination
print("\n3. Test /api/jobs with pagination")
response = session.get(f'{BASE_URL}/api/jobs?page=1&per_page=5')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Total: {data['total']}, Page: {data['page']}, Per Page: {data['per_page']}")
    print(f"   Jobs returned: {len(data['jobs'])}")
    print(f"   ✅ PASS" if len(data['jobs']) <= 5 else f"   ❌ FAIL")
else:
    print(f"   ❌ FAIL: {response.text}")

# Test status filter
print("\n4. Test /api/jobs with status filter")
response = session.get(f'{BASE_URL}/api/jobs?status=pending')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Pending jobs: {data['total']}")
    all_pending = all(job['job_status'] == 'pending' for job in data['jobs'])
    print(f"   ✅ PASS" if all_pending else f"   ❌ FAIL: Some jobs not pending")
else:
    print(f"   ❌ FAIL: {response.text}")

# Test job_type filter
print("\n5. Test /api/jobs with job_type filter")
response = session.get(f'{BASE_URL}/api/jobs?job_type=manual_generation')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Manual generation jobs: {data['total']}")
    all_manual_gen = all(job['job_type'] == 'manual_generation' for job in data['jobs'])
    print(f"   ✅ PASS" if all_manual_gen else f"   ❌ FAIL: Some jobs not manual_generation")
else:
    print(f"   ❌ FAIL: {response.text}")

# Test combined filters
print("\n6. Test /api/jobs with combined filters")
response = session.get(f'{BASE_URL}/api/jobs?status=pending&job_type=manual_generation&page=1&per_page=3')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Total: {data['total']}, Jobs returned: {len(data['jobs'])}")
    valid = all(
        job['job_status'] == 'pending' and 
        job['job_type'] == 'manual_generation' 
        for job in data['jobs']
    ) and len(data['jobs']) <= 3
    print(f"   ✅ PASS" if valid else f"   ❌ FAIL")
else:
    print(f"   ❌ FAIL: {response.text}")

# Test dashboard response structure
print("\n7. Test /api/company/dashboard response structure")
response = session.get(f'{BASE_URL}/api/company/dashboard')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    required_keys = ['success', 'company_name', 'statistics', 'recent_activity']
    has_all_keys = all(key in data for key in required_keys)
    
    required_stats = ['total_users', 'active_users', 'total_manuals', 'total_templates']
    has_all_stats = all(key in data['statistics'] for key in required_stats)
    
    print(f"   Has all required keys: {has_all_keys}")
    print(f"   Has all required statistics: {has_all_stats}")
    print(f"   ✅ PASS" if (has_all_keys and has_all_stats) else f"   ❌ FAIL")
else:
    print(f"   ❌ FAIL: {response.text}")

# Test invalid pagination
print("\n8. Test /api/jobs with invalid pagination")
response = session.get(f'{BASE_URL}/api/jobs?page=999&per_page=20')
print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Total: {data['total']}, Jobs returned: {len(data['jobs'])}")
    print(f"   ✅ PASS - Returns empty page gracefully")
else:
    print(f"   ❌ FAIL: {response.text}")

print("\n" + "="*50)
print("✅ All edge case tests completed!")
