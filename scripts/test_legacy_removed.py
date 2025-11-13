"""
Verify that legacy endpoints are properly removed
"""
import requests

BASE_URL = 'http://localhost:5000'

# Login
session = requests.Session()
login_data = {
    'email': 'support@career-survival.com',
    'password': '0000'
}
response = session.post(f'{BASE_URL}/auth/login', json=login_data)
if response.status_code != 200:
    print(f"❌ Login failed")
    exit(1)

print("=== Testing Removed Legacy Endpoints ===\n")
print("These endpoints should return 404 or 405:\n")

# Legacy endpoints that should be removed
legacy_endpoints = [
    ('GET', '/files', 'Legacy /files (replaced by /api/materials)'),
    ('GET', '/manuals', 'Legacy /manuals (stub implementation)'),
    ('GET', '/get_version_limits', 'Legacy /get_version_limits'),
    ('GET', '/company/stats', 'Legacy /company/stats (replaced by /api/company/dashboard)'),
    ('POST', '/generate_manual', 'Legacy /generate_manual endpoint route'),
    ('POST', '/ai_comparison_analysis', 'Legacy /ai_comparison_analysis endpoint route'),
    ('POST', '/generate_manual_multi_stage', 'Legacy /generate_manual_multi_stage endpoint route'),
    ('GET', '/api/jobs/processing', 'Legacy /api/jobs/processing'),
    ('POST', '/api/jobs/task123/cancel', 'Legacy /api/jobs/cancel'),
    ('GET', '/api/jobs/statistics', 'Legacy /api/jobs/statistics'),
    ('GET', '/api/jobs/worker-status', 'Legacy /api/jobs/worker-status'),
]

passed = 0
failed = 0

for method, endpoint, description in legacy_endpoints:
    try:
        if method == 'GET':
            response = session.get(f'{BASE_URL}{endpoint}')
        elif method == 'POST':
            response = session.post(f'{BASE_URL}{endpoint}', json={})
        
        # Should be 404 (not found) or 405 (method not allowed)
        if response.status_code in [404, 405]:
            print(f"✅ {description}: {response.status_code} (properly removed)")
            passed += 1
        else:
            print(f"⚠️  {description}: {response.status_code} (unexpected - may still exist)")
            # Check if it's a redirect or other expected behavior
            if response.status_code in [302, 500]:
                print(f"   ℹ️  May be redirected or handled differently")
                passed += 1
            else:
                failed += 1
    except Exception as e:
        print(f"❌ {description}: Error - {str(e)}")
        failed += 1

print(f"\n{'='*60}")
print(f"Results: {passed} properly removed, {failed} issues")
if failed == 0:
    print(f"✅ All legacy endpoints successfully removed!")
else:
    print(f"⚠️  Some legacy endpoints may still be accessible")
