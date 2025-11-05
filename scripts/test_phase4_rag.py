"""
File: test_phase4_rag.py
Purpose: Comprehensive test script for Phase 4 RAG system
Main functionality: Test material upload, processing, ElasticSearch indexing, semantic search
Dependencies: requests, json
"""

import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://localhost:5000"


class Phase4Tester:
    """Phase 4 RAG system comprehensive tester"""
    
    def __init__(self):
        self.session = requests.Session()
        self.material_id = None
        self.job_id = None
    
    def print_section(self, title):
        """Print section header"""
        print(f"\n{'=' * 60}")
        print(f" {title}")
        print(f"{'=' * 60}\n")
    
    def print_result(self, test_name, passed, details=""):
        """Print test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"   {details}")
    
    def login(self):
        """Login as test user"""
        self.print_section("Authentication Test")
        
        response = self.session.post(
            f"{BASE_URL}/auth/login",
            json={
                "company_code": "career-survival",
                "password": "0000",
                "username": "support@career-survival.com"
            }
        )
        
        passed = response.status_code == 200
        self.print_result(
            "User Login",
            passed,
            f"Status: {response.status_code}"
        )
        
        if passed:
            print(f"   User: {response.json().get('user')}")
            print(f"   Role: {response.json().get('role')}")
        
        return passed
    
    def test_list_materials(self):
        """Test material list endpoint"""
        self.print_section("Material List Test")
        
        response = self.session.get(f"{BASE_URL}/api/materials")
        
        passed = response.status_code == 200
        self.print_result(
            "GET /api/materials",
            passed,
            f"Status: {response.status_code}"
        )
        
        if passed:
            data = response.json()
            print(f"   Total materials: {data.get('total', 0)}")
            print(f"   Current page: {data.get('page', 0)}")
            print(f"   Per page: {data.get('per_page', 0)}")
        
        return passed
    
    def test_upload_material(self, file_path=None):
        """Test material upload endpoint"""
        self.print_section("Material Upload Test")
        
        # Create or use test file
        if file_path is None:
            # Create a temporary test PDF
            test_file_path = "test_sample.pdf"
            if not os.path.exists(test_file_path):
                print("   Creating test PDF file...")
                # Simple PDF content
                with open(test_file_path, 'w') as f:
                    f.write("%PDF-1.4\n")
                    f.write("Test PDF Content for RAG System\n")
            file_path = test_file_path
        
        if not os.path.exists(file_path):
            self.print_result("Material Upload", False, f"File not found: {file_path}")
            return False
        
        # Upload file
        with open(file_path, 'rb') as f:
            files = {'file': (os.path.basename(file_path), f, 'application/pdf')}
            data = {
                'title': 'Test Reference Material',
                'description': 'Test material for RAG system validation'
            }
            
            response = self.session.post(
                f"{BASE_URL}/api/materials",
                files=files,
                data=data
            )
        
        passed = response.status_code == 201
        
        # Debug: print response details
        if not passed:
            print(f"   Response Body: {response.text[:500]}")
        
        self.print_result(
            "POST /api/materials",
            passed,
            f"Status: {response.status_code}"
        )
        
        if passed:
            result = response.json()
            self.material_id = result['material']['id']
            self.job_id = result.get('job_id')
            
            print(f"   Material ID: {self.material_id}")
            print(f"   Job ID: {self.job_id}")
            print(f"   File: {result['material']['original_filename']}")
            print(f"   Status: {result['material']['processing_status']}")
        
        return passed
    
    def test_get_material_status(self, timeout=30):
        """Test material processing status endpoint"""
        self.print_section("Material Processing Status Test")
        
        if not self.material_id:
            self.print_result("Get Material Status", False, "No material ID available")
            return False
        
        # Poll for status
        start_time = time.time()
        last_status = None
        
        while time.time() - start_time < timeout:
            response = self.session.get(
                f"{BASE_URL}/api/materials/{self.material_id}/status"
            )
            
            if response.status_code != 200:
                self.print_result(
                    "GET /api/materials/{id}/status",
                    False,
                    f"Status: {response.status_code}"
                )
                return False
            
            data = response.json()
            status = data.get('processing_status')
            progress = data.get('processing_progress', 0)
            
            if status != last_status:
                print(f"   Status: {status} ({progress}%)")
                last_status = status
            
            if status == 'completed':
                self.print_result(
                    "GET /api/materials/{id}/status",
                    True,
                    f"Processing completed (Chunks: {data.get('chunk_count', 0)})"
                )
                print(f"   ElasticSearch indexed: {data.get('elasticsearch_indexed')}")
                return True
            
            if status == 'failed':
                self.print_result(
                    "GET /api/materials/{id}/status",
                    False,
                    f"Processing failed: {data.get('error_message')}"
                )
                return False
            
            time.sleep(2)
        
        self.print_result(
            "GET /api/materials/{id}/status",
            False,
            f"Timeout after {timeout}s (Status: {last_status})"
        )
        return False
    
    def test_get_material_details(self):
        """Test material details endpoint"""
        self.print_section("Material Details Test")
        
        if not self.material_id:
            self.print_result("Get Material Details", False, "No material ID available")
            return False
        
        response = self.session.get(
            f"{BASE_URL}/api/materials/{self.material_id}"
        )
        
        passed = response.status_code == 200
        self.print_result(
            "GET /api/materials/{id}",
            passed,
            f"Status: {response.status_code}"
        )
        
        if passed:
            data = response.json()
            print(f"   Title: {data.get('title')}")
            print(f"   File Type: {data.get('file_type')}")
            print(f"   File Size: {data.get('file_size', 0) / 1024:.2f} KB")
            print(f"   Chunk Count: {data.get('chunk_count', 0)}")
            print(f"   Download URL: {'Present' if data.get('download_url') else 'Missing'}")
        
        return passed
    
    def test_update_material(self):
        """Test material update endpoint"""
        self.print_section("Material Update Test")
        
        if not self.material_id:
            self.print_result("Update Material", False, "No material ID available")
            return False
        
        response = self.session.put(
            f"{BASE_URL}/api/materials/{self.material_id}",
            json={
                'title': 'Updated Test Material',
                'description': 'Updated description for testing'
            }
        )
        
        passed = response.status_code == 200
        self.print_result(
            "PUT /api/materials/{id}",
            passed,
            f"Status: {response.status_code}"
        )
        
        if passed:
            data = response.json()
            print(f"   New Title: {data['material'].get('title')}")
        
        return passed
    
    def test_elasticsearch_health(self):
        """Test ElasticSearch connection"""
        self.print_section("ElasticSearch Health Check")
        
        try:
            from src.services.elasticsearch_service import elasticsearch_service
            
            healthy = elasticsearch_service.health_check()
            
            self.print_result(
                "ElasticSearch Connection",
                healthy,
                "Cluster healthy" if healthy else "Cluster unhealthy"
            )
            
            # Try to create index
            created = elasticsearch_service.create_index()
            self.print_result(
                "ElasticSearch Index Creation",
                True,
                f"Index: {elasticsearch_service.index_name}"
            )
            
            return healthy
        
        except Exception as e:
            self.print_result("ElasticSearch Health", False, str(e))
            return False
    
    def test_delete_material(self):
        """Test material deletion endpoint"""
        self.print_section("Material Deletion Test")
        
        if not self.material_id:
            self.print_result("Delete Material", False, "No material ID available")
            return False
        
        response = self.session.delete(
            f"{BASE_URL}/api/materials/{self.material_id}"
        )
        
        passed = response.status_code == 200
        self.print_result(
            "DELETE /api/materials/{id}",
            passed,
            f"Status: {response.status_code}"
        )
        
        return passed
    
    def run_all_tests(self):
        """Run all Phase 4 tests"""
        print("\n" + "=" * 60)
        print(" Phase 4 RAG System Test Suite")
        print("=" * 60)
        
        results = {}
        
        # Authentication
        results['login'] = self.login()
        
        if not results['login']:
            print("\n❌ Authentication failed. Cannot proceed with tests.")
            return results
        
        # ElasticSearch health
        results['elasticsearch_health'] = self.test_elasticsearch_health()
        
        # Material management
        results['list_materials'] = self.test_list_materials()
        results['upload_material'] = self.test_upload_material()
        
        # Wait for processing (only if upload succeeded)
        if results['upload_material']:
            results['processing_status'] = self.test_get_material_status(timeout=60)
        else:
            results['processing_status'] = False
        
        # Material details and updates
        results['get_material'] = self.test_get_material_details()
        results['update_material'] = self.test_update_material()
        
        # Cleanup (optional)
        # results['delete_material'] = self.test_delete_material()
        
        # Summary
        self.print_section("Test Summary")
        
        passed_count = sum(1 for result in results.values() if result)
        total_count = len(results)
        
        print(f"Tests Passed: {passed_count}/{total_count}")
        print(f"Success Rate: {passed_count / total_count * 100:.1f}%\n")
        
        for test_name, result in results.items():
            status = "✅" if result else "❌"
            print(f"{status} {test_name}")
        
        return results


if __name__ == '__main__':
    tester = Phase4Tester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    all_passed = all(results.values())
    exit(0 if all_passed else 1)
