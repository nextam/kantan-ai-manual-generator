#!/usr/bin/env python3
"""
データベース構造とファイル情報の調査
"""
import sqlite3
import os

def check_database_structure():
    print("=== データベース構造の確認 ===")
    print()
    
    # データベース接続
    db_path = r"manual_generator\instance\manual_generator.db"
    if not os.path.exists(db_path):
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. テーブル一覧
    print("1. データベース内のテーブル:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    for table in tables:
        print(f"   - {table[0]}")
    
    print()
    
    # 2. 各テーブルの構造確認
    for table in tables:
        table_name = table[0]
        print(f"2. {table_name}テーブルの構造:")
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        for col in columns:
            print(f"   - {col[1]} ({col[2]})")
        
        # レコード数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"   レコード数: {count}")
        print()
    
    conn.close()

if __name__ == "__main__":
    check_database_structure()