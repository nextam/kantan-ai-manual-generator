from google.cloud import storage
import sqlite3

def check_all_0111_files():
    """
    0111関連の全ファイルのGCS存在確認
    """
    print("=== 0111関連ファイルのGCS存在確認 ===")
    
    try:
        # データベースから0111関連ファイルを取得
        conn = sqlite3.connect('/app/instance/manual_generator.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, stored_filename, file_path, file_size
            FROM uploaded_files 
            WHERE stored_filename LIKE '%0111%'
            ORDER BY id
        """)
        
        files = cursor.fetchall()
        conn.close()
        
        # GCSクライアント初期化
        client = storage.Client.from_service_account_json('/app/gcp-credentials.json')
        bucket = client.bucket('manual_generator')
        
        print(f"📊 対象ファイル数: {len(files)}")
        
        existing_files = []
        missing_files = []
        
        for file_info in files:
            file_id, stored_filename, file_path, file_size = file_info
            
            # GCSでの存在確認
            blob = bucket.blob(file_path)
            exists = blob.exists()
            
            status = "✅ 存在" if exists else "❌ なし"
            print(f"ID {file_id}: {status} - {stored_filename}")
            
            if exists:
                existing_files.append(file_info)
                # 実際のファイルサイズも確認
                try:
                    blob.reload()
                    actual_size = blob.size
                    size_match = "サイズ一致" if actual_size == file_size else f"サイズ不一致 DB:{file_size} GCS:{actual_size}"
                    print(f"         {size_match}")
                except:
                    print(f"         サイズ確認エラー")
            else:
                missing_files.append(file_info)
        
        print(f"\n=== サマリー ===")
        print(f"✅ GCSに存在: {len(existing_files)}件")
        print(f"❌ GCSにない: {len(missing_files)}件")
        
        if existing_files:
            print(f"\n利用可能なファイル:")
            for file_info in existing_files[:3]:  # 最初の3件
                print(f"  ID {file_info[0]}: {file_info[1]}")
        
        if missing_files:
            print(f"\n不足ファイル:")
            for file_info in missing_files:
                print(f"  ID {file_info[0]}: {file_info[1]}")
        
        # 解決策の提案
        if existing_files and missing_files:
            print(f"\n💡 解決策:")
            print(f"1. 存在するファイル（ID {existing_files[0][0]}など）を使用")
            print(f"2. または、不足ファイルを別の既存ファイルからコピー")
            
            return existing_files[0]  # 最初の存在するファイルを返す
        
        return None
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    result = check_all_0111_files()
    
    if result:
        print(f"\n🎯 推奨する代替ファイル: ID {result[0]} - {result[1]}")
    else:
        print(f"\n❌ 利用可能なファイルがありません")