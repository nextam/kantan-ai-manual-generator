#!/usr/bin/env python3
import sqlite3
import json

def check_user_company_settings():
    try:
        conn = sqlite3.connect("/app/instance/manual_generator.db")
        cursor = conn.cursor()
        
        # 企業設定を確認
        print("=== 企業設定確認 ===")
        cursor.execute("PRAGMA table_info(companies)")
        company_columns = cursor.fetchall()
        print("Company table columns:")
        for col in company_columns:
            print(f"  {col}")
        
        # 企業の詳細設定を確認
        print("\n=== 企業の詳細情報 ===")
        cursor.execute("SELECT id, name, storage_type, storage_config FROM companies")
        companies = cursor.fetchall()
        for company in companies:
            print(f"Company ID: {company[0]}")
            print(f"  Name: {company[1]}")
            print(f"  Storage Type: {company[2]}")
            print(f"  Storage Config: {company[3]}")
            print("---")
        
        # ユーザー設定を確認
        print("\n=== ユーザー情報 ===")
        cursor.execute("SELECT id, username, company_id FROM users LIMIT 5")
        users = cursor.fetchall()
        for user in users:
            print(f"User ID: {user[0]}")
            print(f"  Username: {user[1]}")
            print(f"  Company ID: {user[2]}")
            print("---")
        
        conn.close()
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    check_user_company_settings()