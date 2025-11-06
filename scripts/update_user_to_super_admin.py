"""
File: update_user_to_super_admin.py
Purpose: Update existing user account to super_admin role
Main functionality: Change role from admin to super_admin
Dependencies: src.core.app, src.models.models
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.app import app
from src.models.models import db, User

def update_to_super_admin():
    """Update support@career-survival.com to super_admin role"""
    with app.app_context():
        # Find the user
        user = User.query.filter_by(email='support@career-survival.com').first()
        
        if not user:
            print("❌ User not found: support@career-survival.com")
            return
        
        print(f"✅ User found: {user.email}")
        print(f"   Current role: {user.role}")
        print(f"   Username: {user.username}")
        print(f"   Company ID: {user.company_id}")
        
        # Update role to super_admin
        user.role = 'super_admin'
        db.session.commit()
        
        print(f"\n✅ Role updated successfully!")
        print(f"   New role: {user.role}")
        
        # Display all users with their roles
        print("\n" + "="*50)
        print("All Users:")
        print("="*50)
        all_users = User.query.filter_by(is_active=True).all()
        for u in all_users:
            role_display = {
                'user': 'General User',
                'admin': 'Company Admin',
                'super_admin': 'Super Admin'
            }.get(u.role, u.role)
            print(f"   - {u.email}")
            print(f"     Role: {role_display} ({u.role})")
            print(f"     Company ID: {u.company_id}")
            print()

if __name__ == '__main__':
    update_to_super_admin()
