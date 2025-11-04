#!/usr/bin/env python3
"""
データベースマイグレーション: マニュアル（画像あり）生成用フィールドの追加
"""

import sqlite3
import os
from pathlib import Path

def migrate_database():
    """データベースにstage1_content, stage2_content, stage3_contentフィールドを追加"""
    
    db_path = Path('instance/manual_generator.db')
    if not db_path.exists():
        print(f"データベースファイルが見つかりません: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # 既存のテーブル構造を確認
        cursor.execute("PRAGMA table_info(manuals)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"既存のカラム: {columns}")
        
        # 新しいフィールドを追加
        new_fields = [
            'stage1_content', 
            'stage2_content', 
            'stage3_content',
            'generation_status',
            'generation_progress', 
            'error_message'
        ]
        
        for field in new_fields:
            if field not in columns:
                print(f"フィールド '{field}' を追加中...")
                if field == 'generation_status':
                    cursor.execute(f"ALTER TABLE manuals ADD COLUMN {field} TEXT DEFAULT 'completed'")
                elif field == 'generation_progress':
                    cursor.execute(f"ALTER TABLE manuals ADD COLUMN {field} INTEGER DEFAULT 100")
                else:
                    cursor.execute(f"ALTER TABLE manuals ADD COLUMN {field} TEXT")
                print(f"フィールド '{field}' を追加しました")
            else:
                print(f"フィールド '{field}' は既に存在します")
        
        # 変更をコミット
        conn.commit()
        
        # 更新後のテーブル構造を確認
        cursor.execute("PRAGMA table_info(manuals)")
        updated_columns = [column[1] for column in cursor.fetchall()]
        print(f"更新後のカラム: {updated_columns}")
        
        conn.close()
        print("データベースマイグレーションが完了しました")
        return True
        
    except Exception as e:
        print(f"マイグレーションエラー: {e}")
        return False

if __name__ == "__main__":
    print("=== データベースマイグレーション開始 ===")
    success = migrate_database()
    
    if success:
        print("✅ マイグレーション成功")
    else:
        print("❌ マイグレーション失敗")
