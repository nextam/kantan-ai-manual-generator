#!/usr/bin/env python3
import sqlite3
import sys

def check_mp4_files():
    try:
        # データベース接続
        conn = sqlite3.connect('/app/instance/manual_generator.db')
        cursor = conn.cursor()
        
        # _mp4 拡張子のファイル数をカウント
        cursor.execute("SELECT COUNT(*) FROM uploaded_files WHERE stored_filename LIKE '%_mp4' OR file_path LIKE '%_mp4'")
        mp4_count = cursor.fetchone()[0]
        
        # 総ファイル数をカウント
        cursor.execute("SELECT COUNT(*) FROM uploaded_files")
        total_count = cursor.fetchone()[0]
        
        print(f"修正対象ファイル数: {mp4_count}")
        print(f"総ファイル数: {total_count}")
        print(f"修正対象割合: {mp4_count/total_count*100:.1f}%" if total_count > 0 else "0%")
        
        # サンプルファイルも表示
        cursor.execute("SELECT stored_filename, file_path FROM uploaded_files WHERE stored_filename LIKE '%_mp4' OR file_path LIKE '%_mp4' LIMIT 5")
        samples = cursor.fetchall()
        
        print("\n=== サンプルファイル ===")
        for i, (stored_name, file_path) in enumerate(samples, 1):
            print(f"{i}. stored_filename: {stored_name}")
            print(f"   file_path: {file_path}")
        
        conn.close()
        
    except Exception as e:
        print(f"エラー: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_mp4_files()