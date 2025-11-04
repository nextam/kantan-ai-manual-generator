import sqlite3
import os

def check_specific_video_file():
    """
    エラーが発生している特定の動画ファイルを調査
    """
    db_path = '/app/instance/manual_generator.db'
    problem_filename = 'b54baf76-ba15-4b9b-9043-5266b72f4ce1_0111____VID_20250620_111337.mp4'
    
    print("=== 問題のファイル詳細調査 ===")
    print(f"🎯 対象ファイル: {problem_filename}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # データベース内の該当ファイル検索
        cursor.execute("""
            SELECT id, original_filename, stored_filename, file_path, file_type, file_size
            FROM uploaded_files 
            WHERE stored_filename LIKE ? OR stored_filename LIKE ?
        """, (f"%{problem_filename}%", f"%{problem_filename.replace('.mp4', '_mp4')}%"))
        
        db_results = cursor.fetchall()
        
        if db_results:
            print(f"✅ データベース内で見つかりました ({len(db_results)}件):")
            for result in db_results:
                print(f"  ID {result[0]}:")
                print(f"    元ファイル名: {result[1]}")
                print(f"    保存ファイル名: {result[2]}")
                print(f"    ファイルパス: {result[3]}")
                print(f"    ファイルタイプ: {result[4]}")
                print(f"    ファイルサイズ: {result[5]}")
                print()
        else:
            print("❌ データベース内で見つかりません")
            
            # 類似ファイルを検索
            search_pattern = problem_filename[:20]  # 最初の20文字で検索
            cursor.execute("""
                SELECT id, original_filename, stored_filename
                FROM uploaded_files 
                WHERE stored_filename LIKE ?
                LIMIT 5
            """, (f"%{search_pattern}%",))
            
            similar_files = cursor.fetchall()
            if similar_files:
                print(f"🔍 類似ファイル ({len(similar_files)}件):")
                for file in similar_files:
                    print(f"  ID {file[0]}: {file[2]}")
        
        # 「0111」を含むファイルを検索（同じ動画の可能性）
        cursor.execute("""
            SELECT id, original_filename, stored_filename, file_path
            FROM uploaded_files 
            WHERE stored_filename LIKE '%0111%' OR original_filename LIKE '%0111%'
        """, )
        
        related_files = cursor.fetchall()
        print(f"\n🔍 '0111'関連ファイル ({len(related_files)}件):")
        for file in related_files:
            print(f"  ID {file[0]}: {file[2]} (元: {file[1]})")
        
        conn.close()
        
        # GCSでの存在確認もテスト
        print(f"\n=== GCS存在確認 ===")
        try:
            from google.cloud import storage
            
            client = storage.Client.from_service_account_json('/app/gcp-credentials.json')
            bucket = client.bucket('manual_generator')
            
            # 問題のファイルパス
            test_paths = [
                f"video/{problem_filename}",
                f"video/{problem_filename.replace('.mp4', '_mp4')}",
            ]
            
            for path in test_paths:
                blob = bucket.blob(path)
                exists = blob.exists()
                print(f"  {path}: {'✅ 存在' if exists else '❌ なし'}")
                
        except Exception as e:
            print(f"GCS確認エラー: {e}")
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_specific_video_file()