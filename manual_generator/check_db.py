#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
from pathlib import Path

def check_database():
    db_path = Path('instance/manual_generator.db')
    
    if not db_path.exists():
        print(f'❌ Database file not found: {db_path}')
        return
    
    print(f'✅ Database file exists: {db_path}')
    print(f'📊 File size: {db_path.stat().st_size} bytes')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # テーブル一覧を確認
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print(f'\n📋 Tables: {[t[0] for t in tables]}')
        
        # 企業テーブルがあるかチェック
        if 'companies' in [t[0] for t in tables]:
            cursor.execute('SELECT company_code, name, password_hash FROM companies')
            companies = cursor.fetchall()
            print(f'\n🏢 Companies found: {len(companies)}')
            if companies:
                print('\n=== ログイン情報 ===')
                for code, name, password_hash in companies:
                    print(f'企業コード: {code}')
                    print(f'企業名: {name}')
                    print(f'パスワード: [ハッシュ化済み]')
                    print(f'ユーザー名: admin (デフォルト)')
                    print('---')
            else:
                print('⚠️ No companies registered')
        else:
            print('❌ No companies table found')
            print('ℹ️ Manual Generator is running in non-auth mode')
            print('ℹ️ You can access directly without login')
        
        conn.close()
        
    except Exception as e:
        print(f'❌ Error checking database: {e}')

if __name__ == '__main__':
    check_database()
