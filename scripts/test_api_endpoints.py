"""
Test new API endpoints
"""
import requests
import json

BASE_URL = 'http://localhost:5000'

# Login
print("=== Login ===")
login_data = {
    'email': 'support@career-survival.com',
    'password': '0000'
}
session = requests.Session()
response = session.post(f'{BASE_URL}/auth/login', json=login_data)
print(f"Status: {response.status_code}")
if response.status_code != 200:
    print(f"Error: {response.text}")
    exit(1)

# Test /api/company/dashboard
print("\n=== Test /api/company/dashboard ===")
response = session.get(f'{BASE_URL}/api/company/dashboard')
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Company: {data.get('company_name')}")
    stats = data.get('statistics', {})
    print(f"Statistics:")
    print(f"  Total Users: {stats.get('total_users')}")
    print(f"  Active Users: {stats.get('active_users')}")
    print(f"  Total Manuals: {stats.get('total_manuals')}")
    print(f"  Total Templates: {stats.get('total_templates')}")
    print(f"  Manuals Today: {stats.get('manuals_today')}")
    print(f"  Materials Today: {stats.get('materials_today')}")
    print(f"  PDFs Today: {stats.get('pdfs_today')}")
    print(f"  Translations Today: {stats.get('translations_today')}")
    print(f"Recent Activity: {len(data.get('recent_activity', []))} items")
else:
    print(f"Error: {response.text}")

# Test /api/jobs
print("\n=== Test /api/jobs ===")
response = session.get(f'{BASE_URL}/api/jobs')
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Total Jobs: {data.get('total')}")
    print(f"Page: {data.get('page')}/{data.get('pages')}")
    print(f"Per Page: {data.get('per_page')}")
    print(f"Jobs in Current Page: {len(data.get('jobs', []))}")
    
    if data.get('jobs'):
        print(f"\nFirst Job:")
        first_job = data['jobs'][0]
        print(f"  ID: {first_job.get('id')}")
        print(f"  Type: {first_job.get('job_type')}")
        print(f"  Status: {first_job.get('job_status')}")
        print(f"  Progress: {first_job.get('progress')}%")
        print(f"  Created: {first_job.get('created_at')}")
else:
    print(f"Error: {response.text}")

# Test /api/jobs with filters
print("\n=== Test /api/jobs?status=completed ===")
response = session.get(f'{BASE_URL}/api/jobs?status=completed')
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Completed Jobs: {data.get('total')}")
else:
    print(f"Error: {response.text}")

print("\n✅ All tests completed!")
