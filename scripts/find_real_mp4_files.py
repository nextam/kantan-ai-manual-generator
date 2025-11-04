#!/usr/bin/env python3
import sqlite3

def find_actual_problematic_files():
    conn = sqlite3.connect('/app/instance/manual_generator.db')
    cursor = conn.cursor()
    
    # _mp4で終わるファイルから実際のサンプルを取得
    cursor.execute("SELECT stored_filename, file_path FROM uploaded_files WHERE stored_filename LIKE '%_mp4' LIMIT 10")
    files = cursor.fetchall()
    
    print("=== Real _mp4 files in database ===")
    for i, (stored_name, file_path) in enumerate(files, 1):
        print(f"{i}. stored_filename: {stored_name}")
        print(f"   file_path: {file_path}")
        print()
    
    # 5b611bbaを含むファイルを検索
    cursor.execute("SELECT stored_filename, file_path FROM uploaded_files WHERE stored_filename LIKE '%5b611bba%' OR file_path LIKE '%5b611bba%'")
    specific_files = cursor.fetchall()
    
    print("=== Files containing 5b611bba ===")
    for i, (stored_name, file_path) in enumerate(specific_files, 1):
        print(f"{i}. stored_filename: {stored_name}")
        print(f"   file_path: {file_path}")
    
    conn.close()

if __name__ == "__main__":
    find_actual_problematic_files()