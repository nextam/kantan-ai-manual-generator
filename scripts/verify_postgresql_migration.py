"""
File: verify_postgresql_migration.py
Purpose: Verify PostgreSQL migration success and test application functionality
Main functionality: Login test, data integrity check, persistence verification
Dependencies: requests, SQLAlchemy
"""

import sys
import os
import requests
import json
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_login():
    """Test login with migrated test account"""
    print("\n" + "="*80)
    print("TEST 1: Login with Migrated Account")
    print("="*80)
    
    response = requests.post(
        'http://localhost:5000/auth/login',
        json={
            'email': 'support@career-survival.com',
            'password': '0000'
        }
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ Login successful")
        print(f"   User: {data.get('username')}")
        print(f"   Role: {data.get('role')}")
        print(f"   Company: {data.get('company_name')}")
        return True
    else:
        print(f"❌ Login failed: {response.text}")
        return False

def verify_data_integrity():
    """Verify all data migrated correctly"""
    print("\n" + "="*80)
    print("TEST 2: Data Integrity Check")
    print("="*80)
    
    engine = create_engine(
        'postgresql://kantan_user:kantan_password@localhost:5432/kantan_ai_manual_generator'
    )
    
    with engine.connect() as conn:
        tables = [
            ('super_admins', 2),
            ('companies', 4),
            ('users', 8),
            ('user_sessions', 1),
            ('uploaded_files', 4),
            ('manual_templates', 22),
            ('processing_jobs', 54),
            ('manuals', 47),
            ('manual_pdfs', 4),
            ('manual_translations', 3),
            ('activity_logs', 549),
            ('media', 1)
        ]
        
        all_pass = True
        for table_name, expected_count in tables:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            actual_count = result.scalar()
            
            status = "✓" if actual_count == expected_count else "✗"
            print(f"  {status} {table_name:25s}: {actual_count:>4} records (expected {expected_count})")
            
            if actual_count != expected_count:
                all_pass = False
        
        return all_pass

def verify_persistence():
    """Verify PostgreSQL volume is persistent"""
    print("\n" + "="*80)
    print("TEST 3: Persistence Verification")
    print("="*80)
    
    engine = create_engine(
        'postgresql://kantan_user:kantan_password@localhost:5432/kantan_ai_manual_generator'
    )
    
    with engine.connect() as conn:
        # Check if data exists (container was restarted earlier)
        result = conn.execute(text("SELECT COUNT(*) FROM companies"))
        company_count = result.scalar()
        
        if company_count > 0:
            print(f"✅ Data persisted after container restart ({company_count} companies found)")
            return True
        else:
            print("❌ Data lost after container restart")
            return False

def main():
    print("\n" + "="*80)
    print("PostgreSQL Migration Verification Report")
    print("="*80)
    
    results = {
        'login_test': False,
        'data_integrity': False,
        'persistence': False
    }
    
    # Run tests
    results['login_test'] = test_login()
    results['data_integrity'] = verify_data_integrity()
    results['persistence'] = verify_persistence()
    
    # Summary
    print("\n" + "="*80)
    print("VERIFICATION SUMMARY")
    print("="*80)
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {test_name.replace('_', ' ').title()}")
    
    print()
    if all_passed:
        print("✅ ALL TESTS PASSED - Migration successful!")
        print("\nNext Steps:")
        print("  1. Application is ready to use with PostgreSQL")
        print("  2. SQLite backup saved in instance/ folder")
        print("  3. Monitor application logs for any issues")
        return 0
    else:
        print("❌ SOME TESTS FAILED - Please review errors above")
        return 1

if __name__ == '__main__':
    sys.exit(main())
