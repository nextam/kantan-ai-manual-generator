"""Test account verification script"""
import sys
import os

# プロジェクトルートをパスに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from src.core.app import app
from src.models.models import db, User, Company, SuperAdmin

with app.app_context():
    # career-survival企業を確認
    company = Company.query.filter_by(company_code='career-survival').first()
    if company:
        print(f"✅ Company found: {company.company_code} (ID: {company.id})")
        print(f"   Name: {company.name}")
        print(f"   Active: {company.is_active}")
        
        # ユーザーを確認
        users = User.query.filter_by(company_id=company.id).all()
        print(f"\n✅ Users in company: {len(users)}")
        for user in users:
            print(f"   - Email: {user.email}")
            print(f"     Username: {user.username}")
            print(f"     Role: {user.role}")
            print(f"     Active: {user.is_active}")
            print()
    else:
        print("❌ Company 'career-survival' not found")
        
        # すべての企業を表示
        all_companies = Company.query.all()
        print(f"\nAll companies ({len(all_companies)}):")
        for c in all_companies:
            print(f"   - {c.company_code} (ID: {c.id}, Active: {c.is_active})")
    
    # SuperAdminを確認
    print("\n" + "="*50)
    print("SuperAdmin Accounts:")
    print("="*50)
    super_admins = SuperAdmin.query.all()
    if super_admins:
        for sa in super_admins:
            print(f"   - Username: {sa.username}")
            print(f"     Email: {sa.email}")
            print(f"     Active: {sa.is_active}")
            print()
    else:
        print("❌ No SuperAdmin accounts found")
