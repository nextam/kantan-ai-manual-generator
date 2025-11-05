"""
File: test_api_comprehensive.py
Purpose: Comprehensive API testing for Manual Generator system
Main functionality: Test all major API endpoints including authentication, file upload, and manual generation
Dependencies: requests, json
"""

import requests
import json
import time
import os
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_CREDENTIALS = {
    'company_code': 'career-survival',
    'username': 'support@career-survival.com',
    'password': '0000'
}

class APITester:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.logged_in = False
        
    def print_header(self, text):
        """Print formatted header"""
        print("\n" + "="*70)
        print(f"  {text}")
        print("="*70)
        
    def print_result(self, success, message):
        """Print test result"""
        icon = "✅" if success else "❌"
        print(f"{icon} {message}")
        
    def test_server_health(self):
        """Test if server is responding"""
        self.print_header("SERVER HEALTH CHECK")
        try:
            response = self.session.get(f"{self.base_url}/", timeout=5)
            self.print_result(True, f"Server is responding (Status: {response.status_code})")
            return True
        except requests.exceptions.ConnectionError:
            self.print_result(False, "Cannot connect to server")
            return False
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_auth_status(self):
        """Test authentication status endpoint"""
        self.print_header("AUTHENTICATION STATUS")
        try:
            response = self.session.get(f"{self.base_url}/auth/status", timeout=5)
            data = response.json()
            
            if response.status_code == 200:
                authenticated = data.get('authenticated', False)
                if authenticated:
                    user = data.get('user', {})
                    company = data.get('company', {})
                    self.print_result(True, f"Authenticated as {user.get('username')} @ {company.get('name')}")
                    self.logged_in = True
                else:
                    self.print_result(True, "Not authenticated (expected before login)")
                return True
            else:
                self.print_result(False, f"Status check failed: {response.status_code}")
                return False
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_login(self):
        """Test login via API"""
        self.print_header("API LOGIN TEST")
        
        # Test with JSON API endpoint
        try:
            response = self.session.post(
                f"{self.base_url}/auth/login",
                json=TEST_CREDENTIALS,
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.print_result(True, f"Login successful: {data.get('user')} @ {data.get('company')}")
                    self.logged_in = True
                    return True
                else:
                    self.print_result(False, f"Login failed: {data.get('error', 'Unknown error')}")
            else:
                self.print_result(False, f"Login request failed (Status: {response.status_code})")
                
            # Fallback: Try form-based login
            print("\nTrying form-based login...")
            response = self.session.post(
                f"{self.base_url}/login",
                data=TEST_CREDENTIALS,
                timeout=5,
                allow_redirects=False
            )
            
            if response.status_code in [200, 302]:
                self.print_result(True, f"Form login successful (Status: {response.status_code})")
                self.logged_in = True
                return True
            else:
                self.print_result(False, f"Form login failed (Status: {response.status_code})")
                return False
                
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_manual_list(self):
        """Test getting manual list"""
        self.print_header("MANUAL LIST API")
        
        if not self.logged_in:
            self.print_result(False, "Not logged in - skipping test")
            return False
        
        try:
            response = self.session.get(f"{self.base_url}/api/manuals", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                manuals = data.get('manuals', [])
                self.print_result(True, f"Retrieved {len(manuals)} manuals")
                
                if manuals:
                    print("\nSample manual:")
                    manual = manuals[0]
                    print(f"  ID: {manual.get('id')}")
                    print(f"  Title: {manual.get('title')}")
                    print(f"  Status: {manual.get('generation_status')}")
                    print(f"  Created: {manual.get('created_at')}")
                
                return True
            else:
                self.print_result(False, f"Failed to get manuals (Status: {response.status_code})")
                return False
                
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def test_file_upload_api(self):
        """Test file upload endpoint"""
        self.print_header("FILE UPLOAD API")
        
        if not self.logged_in:
            self.print_result(False, "Not logged in - skipping test")
            return False
        
        # Create a small test file with video extension
        test_file_path = "scripts/test_video.mp4"
        try:
            # Create a minimal dummy MP4 file
            with open(test_file_path, 'wb') as f:
                # Write minimal valid MP4 header (ftyp box)
                f.write(b'\x00\x00\x00\x20\x66\x74\x79\x70\x69\x73\x6f\x6d\x00\x00\x02\x00')
                f.write(b'\x69\x73\x6f\x6d\x69\x73\x6f\x32\x6d\x70\x34\x31')
                f.write(b'\x00\x00\x00\x08\x66\x72\x65\x65')
                # Add some dummy data to make it a reasonable file size
                f.write(b'\x00' * 1000)
            
            with open(test_file_path, 'rb') as f:
                files = {'file': ('test_video.mp4', f, 'video/mp4')}
                data = {'role': 'expert', 'description': 'API test upload'}
                
                response = self.session.post(
                    f"{self.base_url}/api/upload",
                    files=files,
                    data=data,
                    timeout=30
                )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    file_info = result.get('file')
                    self.print_result(True, f"File uploaded successfully")
                    print(f"  File ID: {file_info.get('id')}")
                    print(f"  Original name: {file_info.get('original_filename')}")
                    print(f"  Stored path: {file_info.get('file_path')}")
                    return True
                else:
                    self.print_result(False, f"Upload failed: {result.get('error')}")
            else:
                self.print_result(False, f"Upload request failed (Status: {response.status_code})")
                print(f"Response: {response.text[:200]}")
            
            return False
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
        finally:
            # Cleanup test file
            if os.path.exists(test_file_path):
                os.remove(test_file_path)
    
    def test_system_info(self):
        """Test system information endpoint"""
        self.print_header("SYSTEM INFORMATION")
        
        try:
            response = self.session.get(f"{self.base_url}/api/system/info", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                self.print_result(True, "System info retrieved")
                
                print("\nSystem Configuration:")
                for key, value in data.items():
                    if key != 'auth_status':
                        print(f"  {key}: {value}")
                
                return True
            else:
                self.print_result(False, f"Failed to get system info (Status: {response.status_code})")
                return False
                
        except Exception as e:
            # This endpoint might not exist
            self.print_result(False, f"Endpoint not available or error: {e}")
            return False
    
    def test_logout(self):
        """Test logout"""
        self.print_header("LOGOUT TEST")
        
        if not self.logged_in:
            self.print_result(False, "Not logged in - skipping test")
            return False
        
        try:
            response = self.session.post(f"{self.base_url}/auth/logout", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    self.print_result(True, "Logout successful")
                    self.logged_in = False
                    return True
            
            self.print_result(False, f"Logout failed (Status: {response.status_code})")
            return False
            
        except Exception as e:
            self.print_result(False, f"Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all API tests"""
        print("\n" + "="*70)
        print("  KANTAN-AI MANUAL GENERATOR - COMPREHENSIVE API TEST")
        print("  Test Account: career-survival / support@career-survival.com")
        print("="*70)
        
        results = {
            'Server Health': self.test_server_health(),
        }
        
        if results['Server Health']:
            results['Auth Status (Before Login)'] = self.test_auth_status()
            results['Login'] = self.test_login()
            
            if results['Login']:
                results['Auth Status (After Login)'] = self.test_auth_status()
                results['Manual List'] = self.test_manual_list()
                results['File Upload'] = self.test_file_upload_api()
                results['System Info'] = self.test_system_info()
                results['Logout'] = self.test_logout()
                results['Auth Status (After Logout)'] = self.test_auth_status()
        
        # Print summary
        self.print_header("TEST SUMMARY")
        passed = sum(1 for r in results.values() if r)
        total = len(results)
        
        for test_name, result in results.items():
            icon = "✅" if result else "❌"
            print(f"{icon} {test_name}")
        
        print(f"\nTotal: {passed}/{total} tests passed ({passed*100//total}%)")
        
        return passed == total


if __name__ == '__main__':
    tester = APITester()
    success = tester.run_all_tests()
    
    exit(0 if success else 1)
