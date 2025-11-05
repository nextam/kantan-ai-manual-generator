"""
File: test_admin_api_production.py
Purpose: Test production super admin API endpoints (Phase 2)
Main functionality: Comprehensive testing of all admin routes
Dependencies: requests, json
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"
TEST_EMAIL = "admin@kantan-ai.net"
TEST_PASSWORD = "admin123"

# Test account credentials
COMPANY_ID = "career-survival"
USER_ID = "support@career-survival.com"
USER_PASSWORD = "0000"

session = requests.Session()

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def print_result(name, success, response=None):
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} - {name}")
    if response:
        print(f"Status: {response.status_code}")
        try:
            data = response.json()
            print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
        except:
            print(f"Response (text): {response.text[:500]}")
    print()

def test_super_admin_login():
    """Test super admin login"""
    print_section("1. Super Admin Login")
    
    response = session.post(
        f"{BASE_URL}/api/test/login-super-admin",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        }
    )
    
    success = response.status_code == 200
    print_result("Super admin login", success, response)
    return success

def test_company_crud():
    """Test company CRUD operations"""
    print_section("2. Company Management API")
    
    # List companies
    response = session.get(f"{BASE_URL}/api/admin/companies?page=1&per_page=10")
    print_result("GET /api/admin/companies - List companies", response.status_code == 200, response)
    
    # Create company
    new_company_data = {
        "name": f"Test Company {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "company_code": f"test-{int(datetime.now().timestamp())}",
        "password": "test1234",
        "admin_email": f"admin-{int(datetime.now().timestamp())}@test.com",
        "admin_password": "admin1234",
        "settings": {
            "manual_format": "detailed",
            "ai_model": "gemini-2.0-flash-exp",
            "max_users": 20
        }
    }
    
    response = session.post(
        f"{BASE_URL}/api/admin/companies",
        json=new_company_data
    )
    print_result("POST /api/admin/companies - Create company", response.status_code == 201, response)
    
    if response.status_code == 201:
        company_id = response.json().get('company', {}).get('id')
        
        # Get company details
        response = session.get(f"{BASE_URL}/api/admin/companies/{company_id}")
        print_result(f"GET /api/admin/companies/{company_id} - Get company details", 
                    response.status_code == 200, response)
        
        # Update company
        update_data = {
            "name": "Updated Test Company",
            "is_active": True,
            "settings": {
                "manual_format": "standard",
                "max_users": 15
            }
        }
        response = session.put(
            f"{BASE_URL}/api/admin/companies/{company_id}",
            json=update_data
        )
        print_result(f"PUT /api/admin/companies/{company_id} - Update company", 
                    response.status_code == 200, response)
        
        # Delete company (soft delete)
        response = session.delete(f"{BASE_URL}/api/admin/companies/{company_id}")
        print_result(f"DELETE /api/admin/companies/{company_id} - Delete company", 
                    response.status_code == 200, response)
    
    # Search companies
    response = session.get(f"{BASE_URL}/api/admin/companies?search=career&status=active")
    print_result("GET /api/admin/companies?search=career&status=active - Search companies", 
                response.status_code == 200, response)

def test_user_management():
    """Test user management operations"""
    print_section("3. User Management API")
    
    # List all users
    response = session.get(f"{BASE_URL}/api/admin/users?page=1&per_page=10")
    print_result("GET /api/admin/users - List all users", response.status_code == 200, response)
    
    # Filter by company
    response = session.get(f"{BASE_URL}/api/admin/users?company_id=1&role=admin")
    print_result("GET /api/admin/users?company_id=1&role=admin - Filter users", 
                response.status_code == 200, response)
    
    # Create user
    new_user_data = {
        "username": f"testuser_{int(datetime.now().timestamp())}",
        "email": f"testuser_{int(datetime.now().timestamp())}@test.com",
        "company_id": 1,  # career-survival company
        "role": "user",
        "password": "test1234",
        "language_preference": "ja"
    }
    
    response = session.post(
        f"{BASE_URL}/api/admin/users",
        json=new_user_data
    )
    print_result("POST /api/admin/users - Create user", response.status_code == 201, response)
    
    if response.status_code == 201:
        user_id = response.json().get('user', {}).get('id')
        
        # Update user
        update_data = {
            "email": f"updated_{int(datetime.now().timestamp())}@test.com",
            "role": "admin",
            "is_active": True,
            "language_preference": "en"
        }
        response = session.put(
            f"{BASE_URL}/api/admin/users/{user_id}",
            json=update_data
        )
        print_result(f"PUT /api/admin/users/{user_id} - Update user", 
                    response.status_code == 200, response)
        
        # Delete user (soft delete)
        response = session.delete(f"{BASE_URL}/api/admin/users/{user_id}")
        print_result(f"DELETE /api/admin/users/{user_id} - Delete user", 
                    response.status_code == 200, response)
    
    # Search users
    response = session.get(f"{BASE_URL}/api/admin/users?search=support")
    print_result("GET /api/admin/users?search=support - Search users", 
                response.status_code == 200, response)

def test_proxy_login():
    """Test proxy login functionality"""
    print_section("4. Proxy Login Functionality")
    
    # Get a user ID to proxy login as
    response = session.get(f"{BASE_URL}/api/admin/users?page=1&per_page=1")
    if response.status_code == 200:
        users = response.json().get('users', [])
        if users:
            target_user_id = users[0]['id']
            
            # Proxy login
            response = session.post(f"{BASE_URL}/api/admin/users/{target_user_id}/proxy-login")
            print_result(f"POST /api/admin/users/{target_user_id}/proxy-login - Proxy login as user", 
                        response.status_code == 200, response)
        else:
            print("WARNING: No users available for proxy login test")
    else:
        print("WARNING: Could not fetch users for proxy login test")

def test_activity_logs():
    """Test activity log endpoints"""
    print_section("5. Activity Logs API")
    
    # List all activity logs
    response = session.get(f"{BASE_URL}/api/admin/activity-logs?page=1&per_page=20")
    print_result("GET /api/admin/activity-logs - List activity logs", 
                response.status_code == 200, response)
    
    # Filter by action type
    response = session.get(f"{BASE_URL}/api/admin/activity-logs?action_type=create_company")
    print_result("GET /api/admin/activity-logs?action_type=create_company - Filter by action", 
                response.status_code == 200, response)
    
    # Filter by date range
    start_date = "2024-01-01T00:00:00"
    end_date = datetime.now().isoformat()
    response = session.get(
        f"{BASE_URL}/api/admin/activity-logs?start_date={start_date}&end_date={end_date}"
    )
    print_result("GET /api/admin/activity-logs?start_date=...&end_date=... - Date range filter", 
                response.status_code == 200, response)
    
    # Export to CSV
    response = session.get(f"{BASE_URL}/api/admin/activity-logs/export?limit=100")
    success = response.status_code == 200 and 'text/csv' in response.headers.get('Content-Type', '')
    print_result("GET /api/admin/activity-logs/export - Export to CSV", success, response)
    
    if success:
        print(f"CSV Preview (first 500 chars):\n{response.text[:500]}\n")

def test_authentication_required():
    """Test that endpoints require authentication"""
    print_section("6. Authentication Verification")
    
    # Create new session without login
    unauth_session = requests.Session()
    
    endpoints = [
        ("GET", "/api/admin/companies"),
        ("POST", "/api/admin/companies"),
        ("GET", "/api/admin/users"),
        ("POST", "/api/admin/users"),
        ("GET", "/api/admin/activity-logs")
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            response = unauth_session.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = unauth_session.post(f"{BASE_URL}{endpoint}", json={})
        
        # Should redirect to login or return 401/403
        success = response.status_code in [401, 403, 302]
        print_result(f"{method} {endpoint} - Authentication required", success, response)

def run_all_tests():
    """Run all API tests"""
    print("\n" + "=" * 60)
    print("  PHASE 2 PRODUCTION API TEST SUITE")
    print("  Comprehensive Super Admin Endpoint Testing")
    print("=" * 60)
    
    # Login first
    if not test_super_admin_login():
        print("\nLogin failed - cannot continue tests")
        return
    
    # Run all test suites
    test_company_crud()
    test_user_management()
    test_proxy_login()
    test_activity_logs()
    test_authentication_required()
    
    print("\n" + "=" * 60)
    print("  TEST SUITE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
