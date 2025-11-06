#!/usr/bin/env python3
"""
データベース初期化スクリプト
企業テナントとユーザーアカウントの初期データを作成します
"""

import os
import sys
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from src.models.models import db, Company, User

# Load environment variables
load_dotenv()

# 環境に応じてアプリケーションをインポート
try:
    from app_with_auth import app
except ImportError:
    from app import app

def init_database():
    """データベースとテーブルを初期化"""
    with app.app_context():
        # 既存のテーブルを削除して再作成
        db.drop_all()
        db.create_all()
        
        print("データベーステーブルを作成しました。")
        
        # Get support email from environment variable
        support_email = os.getenv('SUPPORT_EMAIL', 'support@career-survival.com')
        
        # サンプル企業の作成（スーパー管理者用の企業も含む）
        sample_companies = [
            {
                'name': 'Career Survival Inc.',
                'company_code': 'career-survival',
                'password': '0000',
                'is_super_admin_company': True
            },
            {
                'name': '株式会社テスト',
                'company_code': 'TEST',
                'password': 'test0000',
                'is_super_admin_company': False
            },
            {
                'name': '株式会社サンプル',
                'company_code': 'SAMPLE',
                'password': 'sample0000',
                'is_super_admin_company': False
            },
            {
                'name': '株式会社デモ',
                'company_code': 'DEMO',
                'password': 'demo0000',
                'is_super_admin_company': False
            }
        ]
        
        companies = []
        for company_data in sample_companies:
            company = Company(
                name=company_data['name'],
                company_code=company_data['company_code'],
                password_hash=generate_password_hash(company_data['password'])
            )
            db.session.add(company)
            companies.append(company)
        
        # データベースに保存（企業IDを取得するため）
        db.session.commit()
        
        # スーパー管理者ユーザーの作成（User.role='super_admin'）
        super_admin_user = User(
            username='support',
            email=support_email,
            company_id=companies[0].id,  # Career Survival Inc.
            role='super_admin'
        )
        super_admin_user.set_password('0000')
        db.session.add(super_admin_user)
        
        # 各企業にサンプルユーザーを作成
        sample_users = [
            # テスト株式会社 のユーザー
            {
                'username': 'admin',
                'email': 'admin@test.com',
                'password': '0000',
                'company_id': companies[1].id,
                'role': 'admin'
            },
            # サンプル企業 のユーザー
            {
                'username': 'admin',
                'email': 'admin@sample.com',
                'password': '0000',
                'company_id': companies[2].id,
                'role': 'admin'
            },
            # デモ企業 のユーザー
            {
                'username': 'admin',
                'email': 'admin@demo.com',
                'password': '0000',
                'company_id': companies[3].id,
                'role': 'admin'
            }
        ]
        
        for user_data in sample_users:
            user = User(
                username=user_data['username'],
                email=user_data['email'],
                company_id=user_data['company_id'],
                role=user_data['role']
            )
            user.set_password(user_data['password'])
            db.session.add(user)
        
        # 最終的にコミット
        db.session.commit()
        
        print("初期データを作成しました：")
        print("\n=== スーパー管理者 ===")
        print(f"Email: {support_email}")
        print("Password: 0000")
        print("Role: super_admin")
        print("アクセス: http://localhost:5000/login")
        
        print("\n=== 企業アカウント ===")
        for i, company_data in enumerate(sample_companies):
            print(f"\n企業名: {company_data['name']}")
            print(f"企業コード: {company_data['company_code']}")
            print(f"パスワード: {company_data['password']}")
        
        print("\n=== ユーザーアカウント（企業管理者）===")
        for user_data in sample_users:
            company = next(c for c in companies if c.id == user_data['company_id'])
            print(f"\nEmail: {user_data['email']}")
            print(f"Password: {user_data['password']}")
            print(f"Role: {user_data['role']}")
            print(f"所属企業: {company.name}")
        
        print("\n=== ログイン方法 ===")
        print("すべてのユーザー（スーパー管理者、企業管理者、一般ユーザー）:")
        print("   URL: http://localhost:5000/login")
        print("   メールアドレスとパスワードでログイン")

if __name__ == '__main__':
    init_database()
    print("\nデータベース初期化が完了しました。")