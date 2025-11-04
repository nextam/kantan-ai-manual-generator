#!/usr/bin/env python3
"""
企業テーブルからストレージ設定カラムを削除するマイグレーション
storage_type と storage_config カラムを削除し、常にGCS使用に統一
"""

import sqlite3
import os
from datetime import datetime

def migrate_remove_storage_columns():
    """企業テーブルからストレージ設定カラムを削除"""
    db_path = "/app/instance/manual_generator.db"
    backup_path = f"/app/instance/manual_generator_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    
    try:
        # バックアップ作成
        print("=== データベースバックアップ作成 ===")
        if os.path.exists(db_path):
            import shutil
            shutil.copy2(db_path, backup_path)
            print(f"✅ バックアップ作成完了: {backup_path}")
        
        # データベース接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 現在のテーブル構造を確認
        print("\n=== 変更前のテーブル構造 ===")
        cursor.execute("PRAGMA table_info(companies)")
        columns_before = cursor.fetchall()
        for col in columns_before:
            print(f"  {col}")
        
        # SQLiteでは直接カラム削除ができないため、新しいテーブルを作成して移行
        print("\n=== テーブル再構築開始 ===")
        
        # 新しいテーブル構造（ストレージ設定カラムを削除）
        cursor.execute("""
        CREATE TABLE companies_new (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            company_code VARCHAR(50) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            settings TEXT
        )
        """)
        print("✅ 新しいcompaniesテーブル作成完了")
        
        # データ移行（ストレージ設定カラムを除く）
        cursor.execute("""
        INSERT INTO companies_new (
            id, name, company_code, password_hash, 
            created_at, updated_at, is_active, settings
        )
        SELECT 
            id, name, company_code, password_hash,
            created_at, updated_at, is_active, settings
        FROM companies
        """)
        print("✅ データ移行完了")
        
        # 元テーブルを削除
        cursor.execute("DROP TABLE companies")
        print("✅ 旧companiesテーブル削除完了")
        
        # 新テーブルをリネーム
        cursor.execute("ALTER TABLE companies_new RENAME TO companies")
        print("✅ テーブルリネーム完了")
        
        # インデックスの再作成
        cursor.execute("CREATE UNIQUE INDEX idx_company_name ON companies(name)")
        cursor.execute("CREATE UNIQUE INDEX idx_company_code ON companies(company_code)")
        print("✅ インデックス再作成完了")
        
        # 変更後のテーブル構造確認
        print("\n=== 変更後のテーブル構造 ===")
        cursor.execute("PRAGMA table_info(companies)")
        columns_after = cursor.fetchall()
        for col in columns_after:
            print(f"  {col}")
        
        # データ件数確認
        cursor.execute("SELECT COUNT(*) FROM companies")
        count = cursor.fetchone()[0]
        print(f"\n✅ マイグレーション完了: {count}件のデータを移行")
        
        # 変更をコミット
        conn.commit()
        conn.close()
        
        print(f"\n🎉 マイグレーション成功！")
        print(f"📁 バックアップファイル: {backup_path}")
        
    except Exception as e:
        print(f"❌ マイグレーションエラー: {e}")
        import traceback
        traceback.print_exc()
        
        # ロールバック
        if os.path.exists(backup_path):
            try:
                import shutil
                shutil.copy2(backup_path, db_path)
                print(f"🔄 バックアップからリストア完了")
            except Exception as restore_error:
                print(f"❌ リストアエラー: {restore_error}")

if __name__ == "__main__":
    migrate_remove_storage_columns()