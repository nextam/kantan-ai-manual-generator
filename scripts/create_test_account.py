"""
File: create_test_account.py
Purpose: Create test account for system verification
Main functionality: Creates company 'career-survival' and user 'support@career-survival.com'
Dependencies: Flask app, SQLAlchemy models
"""

import sys
import os

# Add parent directory to path to import from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.models import db, Company, User
from src.core.app import app

def create_test_account():
    """
    Create test account for system verification.
    
    Creates:
        - Company: career-survival (password: 0000)
        - User: support@career-survival.com (username: support@career-survival.com)
    """
    with app.app_context():
        try:
            # Check if company already exists
            existing_company = Company.query.filter_by(company_code='career-survival').first()
            
            if existing_company:
                print(f"Company 'career-survival' already exists (ID: {existing_company.id})")
                company = existing_company
            else:
                # Create company
                company = Company(
                    name='Career Survival Inc.',
                    company_code='career-survival'
                )
                company.set_password('0000')
                
                # Set default settings
                company.set_settings({
                    'manual_format': 'standard',
                    'ai_model': 'gemini-2.5-pro',
                    'storage_quota_gb': 100,
                    'max_users': 50
                })
                
                db.session.add(company)
                db.session.flush()
                
                print(f"✓ Created company: career-survival (ID: {company.id})")
            
            # Check if user already exists
            existing_user = User.query.filter_by(
                username='support@career-survival.com',
                company_id=company.id
            ).first()
            
            if existing_user:
                print(f"User 'support@career-survival.com' already exists (ID: {existing_user.id})")
                print(f"  Role: {existing_user.role}")
                print(f"  Active: {existing_user.is_active}")
            else:
                # Create admin user
                user = User(
                    username='support@career-survival.com',
                    email='support@career-survival.com',
                    company_id=company.id,
                    role='admin',
                    is_active=True
                )
                
                db.session.add(user)
                db.session.commit()
                
                print(f"✓ Created user: support@career-survival.com (ID: {user.id})")
                print(f"  Role: admin")
                print(f"  Email: support@career-survival.com")
            
            print("\n" + "="*50)
            print("Test Account Credentials:")
            print("="*50)
            print(f"Company ID: career-survival")
            print(f"User ID: support@career-survival.com")
            print(f"Password: 0000")
            print(f"Role: Admin")
            print("="*50)
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating test account: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = create_test_account()
    sys.exit(0 if success else 1)
