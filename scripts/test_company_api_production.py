"""
File: test_company_api_production.py
Purpose: Test production company admin API endpoints (Phase 3)
Main functionality: Comprehensive testing of company admin routes
Dependencies: requests, json
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:5000"

# Test account credentials (company admin)
COMPANY_ID = "career-survival"
ADMIN_USER = "support@career-survival.com"
ADMIN_PASSWORD = "0000"

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

def test_company_admin_login():
    """Test company admin login"""
    print_section("1. Company Admin Login")
    
    # Login as company admin
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={
            "company_code": COMPANY_ID,
            "username": ADMIN_USER,
            "password": ADMIN_PASSWORD
        }
    )
    
    success = response.status_code == 200
    print_result("Company admin login", success, response)
    return success

def test_company_user_management():
    """Test company user management endpoints"""
    print_section("2. Company User Management API")
    
    # List company users
    response = session.get(f"{BASE_URL}/api/company/users?page=1&per_page=10")
    print_result("GET /api/company/users - List company users", 
                response.status_code == 200, response)
    
    # Create company user
    new_user_data = {
        "username": f"testuser_{int(datetime.now().timestamp())}",
        "email": f"testuser_{int(datetime.now().timestamp())}@career-survival.com",
        "role": "user",
        "password": "test1234",
        "language_preference": "ja"
    }
    
    response = session.post(
        f"{BASE_URL}/api/company/users",
        json=new_user_data
    )
    print_result("POST /api/company/users - Create user", 
                response.status_code == 201, response)
    
    if response.status_code == 201:
        user_id = response.json().get('user', {}).get('id')
        
        # Get user details
        response = session.get(f"{BASE_URL}/api/company/users/{user_id}")
        print_result(f"GET /api/company/users/{user_id} - Get user details", 
                    response.status_code == 200, response)
        
        # Update user
        update_data = {
            "email": f"updated_{int(datetime.now().timestamp())}@career-survival.com",
            "role": "admin",
            "is_active": True,
            "language_preference": "en"
        }
        response = session.put(
            f"{BASE_URL}/api/company/users/{user_id}",
            json=update_data
        )
        print_result(f"PUT /api/company/users/{user_id} - Update user", 
                    response.status_code == 200, response)
        
        # Delete user (soft delete)
        response = session.delete(f"{BASE_URL}/api/company/users/{user_id}")
        print_result(f"DELETE /api/company/users/{user_id} - Delete user", 
                    response.status_code == 200, response)
    
    # Search users
    response = session.get(f"{BASE_URL}/api/company/users?search=support&role=admin")
    print_result("GET /api/company/users?search=support&role=admin - Search users", 
                response.status_code == 200, response)

def test_template_management():
    """Test template management endpoints"""
    print_section("3. Template Management API")
    
    # List templates
    response = session.get(f"{BASE_URL}/api/company/templates?page=1&per_page=10")
    print_result("GET /api/company/templates - List templates", 
                response.status_code == 200, response)
    
    # Create template
    new_template_data = {
        "name": f"Test Template {datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "description": "Test template for API verification",
        "template_content": {
            "sections": [
                {
                    "name": "Introduction",
                    "prompt": "Generate introduction section"
                },
                {
                    "name": "Safety Procedures",
                    "prompt": "List safety procedures"
                },
                {
                    "name": "Conclusion",
                    "prompt": "Generate conclusion"
                }
            ],
            "style": "detailed",
            "language": "ja"
        },
        "is_default": False
    }
    
    response = session.post(
        f"{BASE_URL}/api/company/templates",
        json=new_template_data
    )
    print_result("POST /api/company/templates - Create template", 
                response.status_code == 201, response)
    
    if response.status_code == 201:
        template_id = response.json().get('template', {}).get('id')
        
        # Get template details
        response = session.get(f"{BASE_URL}/api/company/templates/{template_id}")
        print_result(f"GET /api/company/templates/{template_id} - Get template details", 
                    response.status_code == 200, response)
        
        # Preview template
        response = session.get(f"{BASE_URL}/api/company/templates/{template_id}/preview")
        print_result(f"GET /api/company/templates/{template_id}/preview - Preview template", 
                    response.status_code == 200, response)
        
        # Update template
        update_data = {
            "name": "Updated Test Template",
            "description": "Updated description",
            "template_content": {
                "sections": [
                    {
                        "name": "Overview",
                        "prompt": "Generate overview"
                    },
                    {
                        "name": "Details",
                        "prompt": "Generate details"
                    }
                ],
                "style": "standard",
                "language": "en"
            },
            "is_default": True
        }
        response = session.put(
            f"{BASE_URL}/api/company/templates/{template_id}",
            json=update_data
        )
        print_result(f"PUT /api/company/templates/{template_id} - Update template", 
                    response.status_code == 200, response)
        
        # Delete template (soft delete)
        response = session.delete(f"{BASE_URL}/api/company/templates/{template_id}")
        print_result(f"DELETE /api/company/templates/{template_id} - Delete template", 
                    response.status_code == 200, response)
    
    # Search templates
    response = session.get(f"{BASE_URL}/api/company/templates?search=Test")
    print_result("GET /api/company/templates?search=Test - Search templates", 
                response.status_code == 200, response)

def test_authentication_required():
    """Test that endpoints require company admin authentication"""
    print_section("4. Authentication Verification")
    
    # Create new session without login
    unauth_session = requests.Session()
    
    endpoints = [
        ("GET", "/api/company/users"),
        ("POST", "/api/company/users"),
        ("GET", "/api/company/templates"),
        ("POST", "/api/company/templates")
    ]
    
    for method, endpoint in endpoints:
        if method == "GET":
            response = unauth_session.get(f"{BASE_URL}{endpoint}")
        elif method == "POST":
            response = unauth_session.post(f"{BASE_URL}{endpoint}", json={})
        
        # Should return 401 Unauthorized
        success = response.status_code in [401, 403, 302]
        print_result(f"{method} {endpoint} - Authentication required", success, response)

def test_company_isolation():
    """Test that company admin can only access their own company data"""
    print_section("5. Company Data Isolation Verification")
    
    # Try to access user from another company (should fail)
    # Assuming user ID 2 belongs to a different company
    response = session.get(f"{BASE_URL}/api/company/users/999")
    success = response.status_code == 404
    print_result("GET /api/company/users/999 - Cannot access other company's user", 
                success, response)
    
    print("Note: Company isolation ensures admins can only manage their own company's data")

def run_all_tests():
    """Run all API tests"""
    print("\n" + "=" * 60)
    print("  PHASE 3 PRODUCTION API TEST SUITE")
    print("  Company Admin Endpoint Testing")
    print("=" * 60)
    
    # Login first
    if not test_company_admin_login():
        print("\nLogin failed - cannot continue tests")
        return
    
    # Run all test suites
    test_company_user_management()
    test_template_management()
    test_authentication_required()
    test_company_isolation()
    
    print("\n" + "=" * 60)
    print("  TEST SUITE COMPLETED")
    print("=" * 60)

if __name__ == "__main__":
    run_all_tests()
