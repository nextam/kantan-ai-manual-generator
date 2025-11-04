#!/usr/bin/env python3
"""
マニュアルテーブルにdescriptionカラムを追加するマイグレーションスクリプト
"""

import os
import sys
import sqlite3
from pathlib import Path

def migrate_database():
    """データベースにdescriptionカラムを追加"""
    try:
        # データベースファイルのパスを決定
        if os.path.exists('/app'):
            # コンテナ環境
            db_path = '/app/instance/manual_generator.db'
        else:
            # ローカル環境
            instance_dir = Path(__file__).parent / 'instance'
            db_path = instance_dir / 'manual_generator.db'
        
        # データベースファイルの存在確認
        if not os.path.exists(db_path):
            print(f"データベースファイルが見つかりません: {db_path}")
            return False
        
        # データベースに接続
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 既存のmanuals テーブル構造を確認
        cursor.execute("PRAGMA table_info(manuals);")
        columns = [column[1] for column in cursor.fetchall()]
        
        # descriptionカラムが既に存在するかチェック
        if 'description' in columns:
            print("descriptionカラムは既に存在します。")
            conn.close()
            return True
        
        # descriptionカラムを追加
        print("descriptionカラムを追加します...")
        cursor.execute("ALTER TABLE manuals ADD COLUMN description TEXT;")
        
        # 変更をコミット
        conn.commit()
        conn.close()
        
        print("マイグレーション完了: descriptionカラムが追加されました。")
        return True
        
    except Exception as e:
        print(f"マイグレーションエラー: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    sys.exit(0 if success else 1)
