import sys
sys.path.append('/app')
import sqlite3

try:
    conn = sqlite3.connect('/app/instance/manual_generator.db')
    cursor = conn.cursor()
    
    print("=== Problematic Files Analysis ===")
    # _mp4 という文字列を含むファイルを検索
    cursor.execute("""
        SELECT id, original_filename, stored_filename, file_path 
        FROM uploaded_files 
        WHERE stored_filename LIKE '%_mp4%' OR file_path LIKE '%_mp4%'
        ORDER BY id DESC 
        LIMIT 10
    """)
    
    files = cursor.fetchall()
    print(f"Found {len(files)} files with '_mp4' pattern:")
    for file_id, orig, stored, path in files:
        print(f"ID: {file_id}")
        print(f"  Original: '{orig}'")
        print(f"  Stored: '{stored}'")  
        print(f"  Path: '{path}'")
        print("---")
    
    print("\n=== Normal .mp4 Files ===")
    # 正常な .mp4 ファイルも確認
    cursor.execute("""
        SELECT id, original_filename, stored_filename, file_path
        FROM uploaded_files 
        WHERE (stored_filename LIKE '%.mp4%' OR file_path LIKE '%.mp4%')
        AND stored_filename NOT LIKE '%_mp4%' 
        AND file_path NOT LIKE '%_mp4%'
        ORDER BY id DESC 
        LIMIT 5
    """)
    
    normal_files = cursor.fetchall()
    print(f"Found {len(normal_files)} normal .mp4 files:")
    for file_id, orig, stored, path in normal_files:
        print(f"ID: {file_id}")
        print(f"  Original: '{orig}'")
        print(f"  Stored: '{stored}'")
        print(f"  Path: '{path}'")
        print("---")
    
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()