"""
Check test account role
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.models import db, User
from src.core.app import app

with app.app_context():
    user = User.query.filter_by(email='support@career-survival.com').first()
    
    if user:
        print("=== Test Account Information ===")
        print(f"Username: {user.username}")
        print(f"Email: {user.email}")
        print(f"Role: {user.role}")
        print(f"Company ID: {user.company_id}")
        print(f"Is Active: {user.is_active}")
        
        # Check if role is in allowed roles
        allowed_roles = ['admin', 'user']
        if user.role in allowed_roles:
            print(f"\n✅ Role '{user.role}' is in allowed roles: {allowed_roles}")
        else:
            print(f"\n❌ Role '{user.role}' is NOT in allowed roles: {allowed_roles}")
            print(f"Expected roles: {allowed_roles}")
    else:
        print("❌ User not found")
