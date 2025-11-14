"""
Check if test account exists and verify credentials
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from src.models.models import db, User, Company
from src.core.app import app

with app.app_context():
    print("=== Test Account Verification ===\n")
    
    # Check company
    company = Company.query.filter_by(company_code='career-survival').first()
    if not company:
        print("❌ Company 'career-survival' not found")
        sys.exit(1)
    
    print(f"✅ Company found: {company.name} (ID: {company.id})")
    
    # Check user
    user = User.query.filter_by(email='support@career-survival.com', company_id=company.id).first()
    if not user:
        print("❌ User 'support@career-survival.com' not found")
        sys.exit(1)
    
    print(f"✅ User found: {user.name} ({user.email})")
    print(f"   Role: {user.role}")
    print(f"   Company ID (DB): {user.company_id}")
    
    # Test password
    from werkzeug.security import check_password_hash
    password_valid = check_password_hash(user.password, '0000')
    
    if password_valid:
        print("✅ Password is correct")
    else:
        print("❌ Password is incorrect")
        sys.exit(1)
    
    print("\n=== Test Account Ready ===")
    print(f"Login with:")
    print(f"  Company ID: career-survival")
    print(f"  Email: support@career-survival.com")
    print(f"  Password: 0000")
