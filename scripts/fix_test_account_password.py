"""
File: fix_test_account_password.py
Purpose: Fix test account password for support@career-survival.com
Main functionality: Set password hash for test account
Dependencies: Flask app, SQLAlchemy models
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.app import app
from src.models.models import db, User

with app.app_context():
    # Find the test account
    user = User.query.filter_by(email='support@career-survival.com').first()
    
    if not user:
        print("❌ User 'support@career-survival.com' not found")
        
        # Show all users
        all_users = User.query.all()
        print(f"\nAll users ({len(all_users)}):")
        for u in all_users:
            print(f"   - Email: {u.email}, Username: {u.username}, Company ID: {u.company_id}")
    else:
        print(f"✅ User found: {user.email}")
        print(f"   Username: {user.username}")
        print(f"   Company ID: {user.company_id}")
        print(f"   Role: {user.role}")
        print(f"   Current password_hash: {'Set' if user.password_hash else 'NOT SET'}")
        
        # Set password to "0000"
        user.set_password("0000")
        db.session.commit()
        
        print("\n✅ Password updated successfully!")
        print("   New password: 0000")
        print(f"   Password hash: {user.password_hash[:50]}..." if user.password_hash else "ERROR: Hash not set")
        
        # Verify password
        if user.check_password("0000"):
            print("\n✅ Password verification successful!")
        else:
            print("\n❌ Password verification failed!")
