"""Check test account - use correct database"""
import sys
import os

# プロジェクトルートから実行する
project_root = os.path.abspath('.')
sys.path.insert(0, project_root)

# インスタンスフォルダをプロジェクトルートに設定
os.environ['INSTANCE_PATH'] = os.path.join(project_root, 'instance')

from src.core.app import app
from src.models.models import db, User, Company

print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

with app.app_context():
    # テスト企業を確認
    company = Company.query.filter_by(company_code='career-survival').first()
    
    if company:
        print(f"\n✅ Company found:")
        print(f"   Code: {company.company_code}")
        print(f"   ID: {company.id}")
        print(f"   Name: {company.name}")
        print(f"   Active: {company.is_active}")
        
        # ユーザーを確認
        users = User.query.filter_by(company_id=company.id).all()
        print(f"\n✅ Users: {len(users)}")
        for user in users:
            print(f"   - {user.email}")
            print(f"     Role: {user.role}")
            print(f"     Active: {user.is_active}")
    else:
        print("\n❌ Company 'career-survival' NOT found")
        
        # すべての企業を表示
        all_companies = Company.query.all()
        print(f"\nAll companies ({len(all_companies)}):")
        for c in all_companies[:5]:  # 最初の5つのみ
            print(f"   - {c.company_code} (ID: {c.id})")
