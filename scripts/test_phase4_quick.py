"""
Quick Phase 4 validation test
"""
import requests
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

BASE_URL = "http://localhost:5000"

def test_login():
    """Test authentication"""
    print("\n1. Testing authentication...")
    
    # Create session to persist cookies
    session = requests.Session()
    
    response = session.post(
        f"{BASE_URL}/auth/login",
        json={
            "company_code": "career-survival",
            "password": "0000",
            "username": "support@career-survival.com"
        }
    )
    
    if response.status_code == 200:
        print("   ✅ Login successful")
        return session
    else:
        print(f"   ❌ Login failed: {response.status_code}")
        return None

def test_list_materials(session):
    """Test material list endpoint"""
    print("\n2. Testing GET /api/materials...")
    response = session.get(
        f"{BASE_URL}/api/materials"
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"   ✅ List materials successful")
        print(f"   Total materials: {data.get('total', 0)}")
        return True
    else:
        print(f"   ❌ List materials failed: {response.status_code}")
        print(f"   Response: {response.text}")
        return False

def test_elasticsearch():
    """Test ElasticSearch connection"""
    print("\n3. Testing ElasticSearch...")
    try:
        from src.services.elasticsearch_service import elasticsearch_service
        
        if elasticsearch_service.health_check():
            print("   ✅ ElasticSearch healthy")
            return True
        else:
            print("   ❌ ElasticSearch unhealthy")
            return False
    except Exception as e:
        print(f"   ❌ ElasticSearch error: {e}")
        return False

def test_s3_manager():
    """Test S3 manager"""
    print("\n4. Testing S3 Manager...")
    try:
        from src.infrastructure.s3_manager import s3_manager
        
        # Test path generation
        path = s3_manager.get_material_path(1, 42, "test.pdf")
        expected = "1/materials/42/test.pdf"
        
        if path == expected:
            print(f"   ✅ S3 path generation: {path}")
        else:
            print(f"   ❌ S3 path mismatch: {path} != {expected}")
            return False
        
        # Test validation
        if s3_manager.validate_company_access(1, path):
            print("   ✅ S3 access validation working")
            return True
        else:
            print("   ❌ S3 access validation failed")
            return False
    except Exception as e:
        print(f"   ❌ S3 Manager error: {e}")
        return False

def test_rag_processor():
    """Test RAG processor"""
    print("\n5. Testing RAG Processor...")
    try:
        from src.services.rag_processor import rag_processor
        
        # Test chunking
        test_text = "This is a test paragraph.\n\nThis is another paragraph.\n\nAnd a third one."
        chunks = rag_processor.chunk_text(test_text, chunk_size=20, overlap=5)
        
        if len(chunks) > 0:
            print(f"   ✅ Text chunking: {len(chunks)} chunks created")
            return True
        else:
            print("   ❌ No chunks created")
            return False
    except Exception as e:
        print(f"   ❌ RAG Processor error: {e}")
        return False

def test_celery_config():
    """Test Celery configuration"""
    print("\n6. Testing Celery configuration...")
    try:
        from src.workers.celery_app import celery
        
        if celery.conf.broker_url:
            print(f"   ✅ Celery broker: {celery.conf.broker_url}")
            return True
        else:
            print("   ❌ Celery broker not configured")
            return False
    except Exception as e:
        print(f"   ❌ Celery config error: {e}")
        return False

def main():
    print("=" * 60)
    print(" Phase 4 Quick Validation Test")
    print("=" * 60)
    
    results = []
    
    # Test ElasticSearch
    results.append(("ElasticSearch", test_elasticsearch()))
    
    # Test S3 Manager
    results.append(("S3 Manager", test_s3_manager()))
    
    # Test RAG Processor
    results.append(("RAG Processor", test_rag_processor()))
    
    # Test Celery
    results.append(("Celery Config", test_celery_config()))
    
    # Test API endpoints
    session = test_login()
    if session:
        results.append(("Authentication", True))
        results.append(("List Materials", test_list_materials(session)))
    else:
        results.append(("Authentication", False))
        results.append(("List Materials", False))
    
    # Summary
    print("\n" + "=" * 60)
    print(" Test Summary")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    print(f"\nTests Passed: {passed}/{total}")
    print(f"Success Rate: {passed / total * 100:.1f}%\n")
    
    for test_name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {test_name}")
    
    print()
    
    return 0 if passed == total else 1

if __name__ == '__main__':
    sys.exit(main())
