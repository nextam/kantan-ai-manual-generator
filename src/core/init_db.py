#!/usr/bin/env python3
"""
データベース初期化スクリプト
企業テナントとユーザーアカウントの初期データを作成します
"""

import os
import sys
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from src.models.models import db, Company, User, SuperAdmin

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
        support_email = os.getenv('SUPPORT_EMAIL', 'support@example.com')
        
        # スーパー管理者の作成
        super_admin = SuperAdmin(
            username='admin',
            email=support_email,
            password_hash=generate_password_hash('0000')
        )
        db.session.add(super_admin)
        
        # サンプル企業の作成
        sample_companies = [
            {
                'name': '株式会社テスト',
                'company_code': 'TEST',
                'password': 'test0000'
            },
            {
                'name': '株式会社サンプル',
                'company_code': 'SAMPLE',
                'password': 'sample0000'
            },
            {
                'name': '株式会社デモ',
                'company_code': 'DEMO',
                'password': 'demo0000'
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
        
        # 各企業にサンプルユーザーを作成
        sample_users = [
            # サンプル企業A のユーザー
            {
                'username': 'admin',
                'password': '0000',
                'company_id': companies[0].id
            },
            # テスト株式会社 のユーザー
            {
                'username': 'admin',
                'password': '0000',
                'company_id': companies[1].id
            },
            # デモ企業 のユーザー
            {
                'username': 'admin',
                'password': '0000',
                'company_id': companies[2].id
            }
        ]
        
        for user_data in sample_users:
            user = User(
                username=user_data['username'],
                company_id=user_data['company_id']
            )
            db.session.add(user)
        
        # 最終的にコミット
        db.session.commit()
        
        print("初期データを作成しました：")
        print("\n=== スーパー管理者 ===")
        print("ユーザー名: admin")
        print("パスワード: 0000")
        print("アクセス: http://localhost:5000/super-admin/login")
        
        print("\n=== 企業アカウント ===")
        for i, company_data in enumerate(sample_companies):
            print(f"\n企業名: {company_data['name']}")
            print(f"企業コード: {company_data['company_code']}")
            print(f"パスワード: {company_data['password']}")
        
        print("\n=== ユーザーアカウント ===")
        print("注意: 現在のシステムでは、企業でログインしてからユーザーを管理します。")
        for user_data in sample_users:
            company = next(c for c in companies if c.id == user_data['company_id'])
            print(f"\nユーザー名: {user_data['username']}")
            print(f"所属企業: {company.name}")
        
        print("\n=== ログイン方法 ===")
        print("1. 企業ログイン:")
        print("   URL: http://localhost:5000/login")
        print("   企業名を選択してパスワードを入力")
        print("\n2. スーパー管理者ログイン:")
        print("   URL: http://localhost:5000/super-admin/login")

if __name__ == '__main__':
    init_database()
    print("\nデータベース初期化が完了しました。")
