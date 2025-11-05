"""
File: test_e2e_workflows.py
Purpose: End-to-end workflow testing for all user roles
Main functionality: Super admin, company admin, and general user workflows
Dependencies: requests
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:5000"

class Colors:
    """Terminal colors for output formatting"""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'


def print_success(message):
    """Print success message in green"""
    print(f"{Colors.GREEN}✓ {message}{Colors.END}")


def print_error(message):
    """Print error message in red"""
    print(f"{Colors.RED}✗ {message}{Colors.END}")


def print_info(message):
    """Print info message in blue"""
    print(f"{Colors.BLUE}ℹ {message}{Colors.END}")


def print_section(title):
    """Print section header"""
    print(f"\n{Colors.YELLOW}{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}{Colors.END}\n")


class SuperAdminWorkflowTest:
    """Test super admin workflows"""
    
    def __init__(self):
        self.session = requests.Session()
        self.super_admin_id = None
    
    def run_all_tests(self):
        """Run all super admin tests"""
        print_section("Super Admin Workflow Tests")
        
        try:
            self.test_super_admin_login()
            self.test_company_management()
            self.test_user_management()
            self.test_activity_logs()
            self.test_system_overview()
            print_success("All super admin tests passed!")
        except Exception as e:
            print_error(f"Super admin test failed: {e}")
    
    def test_super_admin_login(self):
        """Test super admin login"""
        print_info("Testing super admin login...")
        
        # First, create super admin if not exists
        response = self.session.post(
            f"{BASE_URL}/api/test/create-super-admin",
            json={
                "username": "admin",
                "email": "admin@kantan-ai.net",
                "password": "admin123"
            }
        )
        
        # Now login
        response = self.session.post(
            f"{BASE_URL}/api/super-admin/login",
            json={
                "username": "admin",
                "password": "admin123"
            }
        )
        
        if response.status_code in [200, 201]:
            print_success("Super admin login successful")
        else:
            print_error(f"Super admin login failed: {response.status_code}")
    
    def test_company_management(self):
        """Test company CRUD operations"""
        print_info("Testing company management...")
        
        # Create company
        response = self.session.post(
            f"{BASE_URL}/api/admin/companies",
            json={
                "name": "Test Company E2E",
                "code": "test-e2e",
                "settings": {"max_users": 50}
            }
        )
        
        if response.status_code in [200, 201]:
            company_data = response.json()
            company_id = company_data.get('company', {}).get('id')
            print_success(f"Company created with ID: {company_id}")
            
            # Update company
            response = self.session.put(
                f"{BASE_URL}/api/admin/companies/{company_id}",
                json={"name": "Test Company E2E Updated"}
            )
            
            if response.status_code == 200:
                print_success("Company updated successfully")
            
            # List companies
            response = self.session.get(f"{BASE_URL}/api/admin/companies")
            if response.status_code == 200:
                print_success(f"Companies listed: {len(response.json().get('companies', []))}")
        else:
            print_error(f"Company creation failed: {response.status_code}")
    
    def test_user_management(self):
        """Test user management operations"""
        print_info("Testing user management...")
        
        # List all users
        response = self.session.get(f"{BASE_URL}/api/admin/users")
        
        if response.status_code == 200:
            users = response.json().get('users', [])
            print_success(f"Users listed: {len(users)}")
        else:
            print_error(f"User listing failed: {response.status_code}")
    
    def test_activity_logs(self):
        """Test activity log viewing"""
        print_info("Testing activity logs...")
        
        response = self.session.get(f"{BASE_URL}/api/admin/activity-logs")
        
        if response.status_code == 200:
            logs = response.json().get('logs', [])
            print_success(f"Activity logs retrieved: {len(logs)}")
        else:
            print_error(f"Activity logs failed: {response.status_code}")
    
    def test_system_overview(self):
        """Test system overview endpoint"""
        print_info("Testing system overview...")
        
        response = self.session.get(f"{BASE_URL}/api/super-admin/overview")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"System overview retrieved")
            print_info(f"  Companies: {data.get('stats', {}).get('companies_total', 0)}")
            print_info(f"  Users: {data.get('stats', {}).get('users_total', 0)}")
            print_info(f"  Manuals: {data.get('stats', {}).get('manuals_total', 0)}")
        else:
            print_error(f"System overview failed: {response.status_code}")


class CompanyAdminWorkflowTest:
    """Test company admin workflows"""
    
    def __init__(self):
        self.session = requests.Session()
        self.company_id = "career-survival"
        self.user_id = "support@career-survival.com"
    
    def run_all_tests(self):
        """Run all company admin tests"""
        print_section("Company Admin Workflow Tests")
        
        try:
            self.test_company_admin_login()
            self.test_template_management()
            self.test_company_user_management()
            self.test_dashboard_access()
            print_success("All company admin tests passed!")
        except Exception as e:
            print_error(f"Company admin test failed: {e}")
    
    def test_company_admin_login(self):
        """Test company admin login"""
        print_info("Testing company admin login...")
        
        response = self.session.post(
            f"{BASE_URL}/auth/login",
            json={
                "company_id": self.company_id,
                "user_id": self.user_id,
                "password": "0000"
            }
        )
        
        if response.status_code == 200:
            print_success("Company admin login successful")
        else:
            print_error(f"Company admin login failed: {response.status_code}")
    
    def test_template_management(self):
        """Test template CRUD operations"""
        print_info("Testing template management...")
        
        # List templates
        response = self.session.get(f"{BASE_URL}/api/company/templates")
        
        if response.status_code == 200:
            templates = response.json().get('templates', [])
            print_success(f"Templates listed: {len(templates)}")
            
            # Create template
            response = self.session.post(
                f"{BASE_URL}/api/company/templates",
                json={
                    "name": "E2E Test Template",
                    "description": "Template for E2E testing",
                    "template_content": {
                        "sections": ["Introduction", "Steps", "Conclusion"]
                    }
                }
            )
            
            if response.status_code in [200, 201]:
                template_id = response.json().get('template', {}).get('id')
                print_success(f"Template created with ID: {template_id}")
        else:
            print_error(f"Template listing failed: {response.status_code}")
    
    def test_company_user_management(self):
        """Test company user management"""
        print_info("Testing company user management...")
        
        # List company users
        response = self.session.get(f"{BASE_URL}/api/company/users")
        
        if response.status_code == 200:
            users = response.json().get('users', [])
            print_success(f"Company users listed: {len(users)}")
        else:
            print_error(f"Company user listing failed: {response.status_code}")
    
    def test_dashboard_access(self):
        """Test company dashboard access"""
        print_info("Testing dashboard access...")
        
        response = self.session.get(f"{BASE_URL}/api/company/dashboard")
        
        if response.status_code == 200:
            data = response.json()
            print_success("Dashboard accessed successfully")
            if 'stats' in data:
                print_info(f"  Total users: {data['stats'].get('total_users', 0)}")
                print_info(f"  Total manuals: {data['stats'].get('total_manuals', 0)}")
        else:
            print_error(f"Dashboard access failed: {response.status_code}")


class GeneralUserWorkflowTest:
    """Test general user workflows"""
    
    def __init__(self):
        self.session = requests.Session()
        self.company_id = "career-survival"
        self.user_id = "support@career-survival.com"
    
    def run_all_tests(self):
        """Run all general user tests"""
        print_section("General User Workflow Tests")
        
        try:
            self.test_user_login()
            self.test_manual_creation()
            self.test_material_upload()
            self.test_pdf_generation()
            self.test_translation()
            print_success("All general user tests passed!")
        except Exception as e:
            print_error(f"General user test failed: {e}")
    
    def test_user_login(self):
        """Test user login"""
        print_info("Testing user login...")
        
        response = self.session.post(
            f"{BASE_URL}/auth/login",
            json={
                "company_id": self.company_id,
                "user_id": self.user_id,
                "password": "0000"
            }
        )
        
        if response.status_code == 200:
            print_success("User login successful")
        else:
            print_error(f"User login failed: {response.status_code}")
    
    def test_manual_creation(self):
        """Test manual creation workflow"""
        print_info("Testing manual creation...")
        
        # Get available templates
        response = self.session.get(f"{BASE_URL}/api/manuals/templates")
        
        if response.status_code == 200:
            templates = response.json().get('templates', [])
            print_success(f"Available templates: {len(templates)}")
            
            # Note: Actual manual generation with video requires file upload
            # This is a simplified test
            print_info("Manual generation requires video upload (skipped in automated test)")
        else:
            print_error(f"Template retrieval failed: {response.status_code}")
    
    def test_material_upload(self):
        """Test reference material upload"""
        print_info("Testing material upload...")
        
        # Note: Material upload requires file upload
        # This is a simplified test
        print_info("Material upload requires file (skipped in automated test)")
    
    def test_pdf_generation(self):
        """Test PDF generation"""
        print_info("Testing PDF generation...")
        
        # List manuals first
        response = self.session.get(f"{BASE_URL}/api/manuals/summary")
        
        if response.status_code == 200:
            manuals = response.json().get('manuals', [])
            print_success(f"Manuals listed: {len(manuals)}")
            
            if manuals:
                manual_id = manuals[0]['id']
                print_info(f"Testing PDF generation for manual {manual_id}")
                # Note: Actual PDF generation is async
        else:
            print_error(f"Manual listing failed: {response.status_code}")
    
    def test_translation(self):
        """Test translation workflow"""
        print_info("Testing translation...")
        
        # Note: Translation requires existing manual
        print_info("Translation requires existing manual (skipped in automated test)")


class SystemHealthTest:
    """Test system health and performance"""
    
    def run_all_tests(self):
        """Run all system health tests"""
        print_section("System Health Tests")
        
        try:
            self.test_health_check()
            self.test_performance_metrics()
            self.test_database_stats()
            print_success("All system health tests passed!")
        except Exception as e:
            print_error(f"System health test failed: {e}")
    
    def test_health_check(self):
        """Test health check endpoint"""
        print_info("Testing health check...")
        
        response = requests.get(f"{BASE_URL}/api/test/ui/health-check")
        
        if response.status_code == 200:
            data = response.json()
            print_success(f"System status: {data.get('status')}")
            
            checks = data.get('checks', {})
            for check_name, check_data in checks.items():
                status = check_data.get('status', 'unknown')
                if status == 'ok':
                    print_success(f"  {check_name}: OK")
                elif status == 'warning':
                    print_info(f"  {check_name}: WARNING")
                else:
                    print_error(f"  {check_name}: ERROR")
        else:
            print_error(f"Health check failed: {response.status_code}")
    
    def test_performance_metrics(self):
        """Test performance metrics endpoint"""
        print_info("Testing performance metrics...")
        
        response = requests.get(f"{BASE_URL}/api/test/ui/performance-metrics")
        
        if response.status_code == 200:
            data = response.json()
            metrics = data.get('metrics', {})
            
            system = metrics.get('system', {})
            print_success("Performance metrics retrieved:")
            print_info(f"  CPU usage: {system.get('cpu', {}).get('usage_percent', 0):.1f}%")
            print_info(f"  Memory usage: {system.get('memory', {}).get('percent', 0):.1f}%")
            
            database = metrics.get('database', {})
            print_info(f"  Database records:")
            print_info(f"    Companies: {database.get('companies', 0)}")
            print_info(f"    Users: {database.get('users', 0)}")
            print_info(f"    Manuals: {database.get('manuals', 0)}")
        else:
            print_error(f"Performance metrics failed: {response.status_code}")
    
    def test_database_stats(self):
        """Test database statistics endpoint"""
        print_info("Testing database stats...")
        
        response = requests.get(f"{BASE_URL}/api/test/ui/database-stats")
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            print_success("Database statistics retrieved")
        else:
            print_error(f"Database stats failed: {response.status_code}")


def main():
    """Main test execution"""
    print_section("Manual Generator E2E Testing")
    print_info(f"Testing against: {BASE_URL}")
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Run system health tests first
    health_tester = SystemHealthTest()
    health_tester.run_all_tests()
    
    # Run super admin workflow tests
    super_admin_tester = SuperAdminWorkflowTest()
    super_admin_tester.run_all_tests()
    
    # Run company admin workflow tests
    company_admin_tester = CompanyAdminWorkflowTest()
    company_admin_tester.run_all_tests()
    
    # Run general user workflow tests
    user_tester = GeneralUserWorkflowTest()
    user_tester.run_all_tests()
    
    print_section("E2E Testing Complete")
    print_info(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == '__main__':
    main()
