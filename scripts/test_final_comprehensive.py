"""
Final comprehensive test - verify all functionality
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

print("="*60)
print("FINAL COMPREHENSIVE TEST")
print("="*60)

# Login
session = requests.Session()
login_data = {
    'email': 'support@career-survival.com',
    'password': '0000'
}
response = session.post(f'{BASE_URL}/auth/login', json=login_data)
assert response.status_code == 200, "Login failed"
print("✅ Authentication successful\n")

# Test 1: New dashboard endpoint
print("Test 1: GET /api/company/dashboard")
response = session.get(f'{BASE_URL}/api/company/dashboard')
assert response.status_code == 200, f"Dashboard failed: {response.status_code}"
data = response.json()
assert 'statistics' in data, "Missing statistics"
assert 'recent_activity' in data, "Missing recent_activity"
assert 'company_name' in data, "Missing company_name"
print(f"  ✅ Company: {data['company_name']}")
print(f"  ✅ Users: {data['statistics']['total_users']}")
print(f"  ✅ Manuals: {data['statistics']['total_manuals']}")
print(f"  ✅ Activity logs: {len(data['recent_activity'])}")

# Test 2: New jobs list endpoint  
print("\nTest 2: GET /api/jobs")
response = session.get(f'{BASE_URL}/api/jobs')
assert response.status_code == 200, f"Jobs list failed: {response.status_code}"
data = response.json()
assert 'jobs' in data, "Missing jobs"
assert 'total' in data, "Missing total"
assert 'page' in data, "Missing page"
print(f"  ✅ Total jobs: {data['total']}")
print(f"  ✅ Page: {data['page']}/{data['pages']}")
print(f"  ✅ Jobs returned: {len(data['jobs'])}")

# Test 3: Jobs with pagination
print("\nTest 3: GET /api/jobs?page=1&per_page=3")
response = session.get(f'{BASE_URL}/api/jobs?page=1&per_page=3')
assert response.status_code == 200, "Jobs pagination failed"
data = response.json()
assert len(data['jobs']) <= 3, "Pagination not working"
print(f"  ✅ Pagination works: {len(data['jobs'])} jobs returned (max 3)")

# Test 4: Jobs with status filter
print("\nTest 4: GET /api/jobs?status=pending")
response = session.get(f'{BASE_URL}/api/jobs?status=pending')
assert response.status_code == 200, "Jobs status filter failed"
data = response.json()
if data['jobs']:
    assert all(j['job_status'] == 'pending' for j in data['jobs']), "Status filter not working"
    print(f"  ✅ Status filter works: {len(data['jobs'])} pending jobs")
else:
    print(f"  ✅ Status filter works: 0 pending jobs")

# Test 5: Jobs with job_type filter
print("\nTest 5: GET /api/jobs?job_type=manual_generation")
response = session.get(f'{BASE_URL}/api/jobs?job_type=manual_generation')
assert response.status_code == 200, "Jobs type filter failed"
data = response.json()
if data['jobs']:
    assert all(j['job_type'] == 'manual_generation' for j in data['jobs']), "Type filter not working"
    print(f"  ✅ Type filter works: {len(data['jobs'])} manual_generation jobs")
else:
    print(f"  ✅ Type filter works: 0 manual_generation jobs")

# Test 6: Existing endpoints still work
print("\nTest 6: Existing endpoints")
existing_tests = [
    ('/api/company/users', 'Company users'),
    ('/api/company/templates', 'Company templates'),
    ('/api/materials', 'Materials'),
    ('/auth/status', 'Auth status'),
]

for endpoint, name in existing_tests:
    response = session.get(f'{BASE_URL}{endpoint}')
    assert response.status_code == 200, f"{name} failed: {response.status_code}"
    print(f"  ✅ {name}: OK")

# Test 7: Legacy endpoints removed
print("\nTest 7: Legacy endpoints removed")
legacy_tests = [
    '/files',
    '/manuals',
    '/get_version_limits',
    '/company/stats',
]

for endpoint in legacy_tests:
    response = session.get(f'{BASE_URL}{endpoint}')
    assert response.status_code == 404, f"{endpoint} should be 404 but got {response.status_code}"
    print(f"  ✅ {endpoint}: Properly removed (404)")

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("\nSummary:")
print("  ✅ New /api/company/dashboard endpoint working")
print("  ✅ New /api/jobs endpoint working")
print("  ✅ Pagination working")
print("  ✅ Status filtering working")
print("  ✅ Job type filtering working")
print("  ✅ All existing endpoints functional")
print("  ✅ Legacy endpoints properly removed")
print("\n🎉 System is ready for production!")
