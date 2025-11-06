"""
File: create_super_admin.py
Purpose: Create a super admin account for support@career-survival.com
Main functionality: Add super admin credentials to database
Dependencies: src.core.app, src.models.models
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.app import app
from src.models.models import db, SuperAdmin

def create_super_admin():
    """Create super admin account for support@career-survival.com"""
    with app.app_context():
        # Check if super admin already exists
        existing = SuperAdmin.query.filter_by(email='support@career-survival.com').first()
        
        if existing:
            print(f"✅ Super admin already exists: {existing.email}")
            print(f"   Username: {existing.username}")
            print(f"   Active: {existing.is_active}")
            
            # Update password to match test account
            existing.set_password('0000')
            existing.is_active = True
            db.session.commit()
            print("✅ Password updated to '0000'")
            return
        
        # Create new super admin
        super_admin = SuperAdmin(
            username='support',
            email='support@career-survival.com',
            is_active=True
        )
        super_admin.set_password('0000')
        
        db.session.add(super_admin)
        db.session.commit()
        
        print("✅ Super admin created successfully!")
        print(f"   Email: {super_admin.email}")
        print(f"   Username: {super_admin.username}")
        print(f"   Password: 0000")
        print(f"   Active: {super_admin.is_active}")
        
        # List all super admins
        print("\n" + "="*50)
        print("All Super Admin Accounts:")
        print("="*50)
        all_super_admins = SuperAdmin.query.all()
        for sa in all_super_admins:
            print(f"   - {sa.email} (Username: {sa.username}, Active: {sa.is_active})")

if __name__ == '__main__':
    create_super_admin()
