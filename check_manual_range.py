#!/usr/bin/env python3
"""
現在のデータベースで最大のマニュアルIDを確認し、
実際に存在するマニュアルの範囲を調査
"""
import sqlite3
import os

def check_manual_id_range():
    """マニュアルIDの範囲と存在状況を確認"""
    print("=== マニュアルID 存在範囲調査 ===")
    print()
    
    db_path = r"manual_generator\instance\manual_generator.db"
    
    if not os.path.exists(db_path):
        print(f"❌ データベースファイルが見つかりません: {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # マニュアルテーブルの基本統計
        cursor.execute("SELECT COUNT(*) FROM manuals")
        total_count = cursor.fetchone()[0]
        print(f"📊 総マニュアル数: {total_count}")
        
        cursor.execute("SELECT MIN(id), MAX(id) FROM manuals")
        min_id, max_id = cursor.fetchone()
        print(f"📊 IDの範囲: {min_id} 〜 {max_id}")
        print()
        
        # ID 57付近のマニュアルを確認
        print("🔍 ID 50-60付近のマニュアル:")
        cursor.execute("""
            SELECT id, title, created_at, updated_at
            FROM manuals 
            WHERE id BETWEEN 50 AND 60
            ORDER BY id
        """)
        
        nearby_manuals = cursor.fetchall()
        
        if nearby_manuals:
            for manual in nearby_manuals:
                manual_id, title, created_at, updated_at = manual
                print(f"  ✅ ID {manual_id}: {title}")
                print(f"     作成: {created_at}")
        else:
            print("  ❌ ID 50-60の範囲にマニュアルが存在しません")
        
        print()
        
        # 最新のマニュアルを確認
        print("📈 最新のマニュアル（上位10件）:")
        cursor.execute("""
            SELECT id, title, created_at, updated_at
            FROM manuals 
            ORDER BY id DESC
            LIMIT 10
        """)
        
        latest_manuals = cursor.fetchall()
        
        for manual in latest_manuals:
            manual_id, title, created_at, updated_at = manual
            print(f"  ID {manual_id}: {title}")
            print(f"     作成: {created_at}")
        
        print()
        
        # 実際にstage2_contentを持つマニュアルを確認
        print("🎬 stage2_contentを持つマニュアル:")
        cursor.execute("""
            SELECT id, title, stage2_content
            FROM manuals 
            WHERE stage2_content IS NOT NULL AND stage2_content != ''
            ORDER BY id DESC
            LIMIT 5
        """)
        
        stage2_manuals = cursor.fetchall()
        
        if stage2_manuals:
            for manual in stage2_manuals:
                manual_id, title, stage2_content = manual
                print(f"  ID {manual_id}: {title}")
                try:
                    import json
                    stage2_data = json.loads(stage2_content) if isinstance(stage2_content, str) else stage2_content
                    video_path = stage2_data.get('video_path', 'なし')
                    print(f"     video_path: {video_path}")
                except:
                    print(f"     stage2_content: パース失敗")
                print()
        else:
            print("  ❌ stage2_contentを持つマニュアルが見つかりません")
        
        # URL例での実際のテスト（https://manual-generator.chuden-demoapp.com/manual/view/57）
        print("🌐 本番環境とローカル環境の違い:")
        print("  本番URL: https://manual-generator.chuden-demoapp.com/manual/view/57")
        print("  ローカル最大ID:", max_id)
        print("  → 本番環境にはID 57のマニュアルが存在するが、ローカルには存在しない")
        print("  → データベースの同期問題の可能性")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        conn.close()

def check_video_file_uuid():
    """5b611bba-c700-478c-882f-238b7bd11ae8のUUIDを含むファイルを検索"""
    print("=== UUID検索: 5b611bba-c700-478c-882f-238b7bd11ae8 ===")
    print()
    
    db_path = r"manual_generator\instance\manual_generator.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        target_uuid = "5b611bba-c700-478c-882f-238b7bd11ae8"
        
        # uploaded_filesテーブルでUUID検索
        cursor.execute("""
            SELECT id, original_filename, stored_filename, file_path, file_size, manual_id, uploaded_at
            FROM uploaded_files 
            WHERE stored_filename LIKE ? OR file_path LIKE ?
        """, (f"%{target_uuid}%", f"%{target_uuid}%"))
        
        uuid_files = cursor.fetchall()
        
        if uuid_files:
            print("✅ UUID一致ファイル発見:")
            for file_record in uuid_files:
                file_id, original_name, stored_name, file_path, file_size, manual_id, upload_date = file_record
                print(f"  📁 ファイルID {file_id}:")
                print(f"     元ファイル名: {original_name}")
                print(f"     保存ファイル名: {stored_name}")
                print(f"     ファイルパス: {file_path}")
                print(f"     マニュアルID: {manual_id}")
                print(f"     ファイルサイズ: {file_size} bytes")
                print(f"     アップロード日: {upload_date}")
                print()
        else:
            print("❌ 該当UUIDのファイルがローカルデータベースに存在しません")
            print("  → 本番環境固有のデータの可能性")
    
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        
    finally:
        conn.close()

if __name__ == "__main__":
    check_manual_id_range()
    print()
    check_video_file_uuid()