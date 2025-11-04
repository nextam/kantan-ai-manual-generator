#!/usr/bin/env python3
"""
stage2_contentから取得したUUIDがGCSに存在するか確認
"""

from google.cloud import storage
import sys
import os
sys.path.append('/app')

def check_stage2_uuids():
    try:
        # GCSクライアント初期化
        client = storage.Client.from_service_account_json("/app/gcp-credentials.json")
        bucket = client.bucket("manual_generator")
        
        # stage2_contentから取得したUUID一覧
        test_cases = [
            {
                'manual_id': 57,
                'uuid': '5b611bba-c700-478c-882f-238b7bd11ae8',
                'db_path': 'uploads/video/5b611bba-c700-478c-882f-238b7bd11ae8_mp4'
            },
            {
                'manual_id': 56,
                'uuid': 'd417084a-f113-4336-81cc-e87ee1f935ee',
                'db_path': 'uploads/video/d417084a-f113-4336-81cc-e87ee1f935ee_3.mp4'
            },
            {
                'manual_id': 53,
                'uuid': '35ba3d10-9476-4baa-9260-cecf885a2eaa',
                'db_path': 'uploads/video/35ba3d10-9476-4baa-9260-cecf885a2eaa_mp4'
            }
        ]
        
        print(f"=== stage2_contentのUUID照合確認 ===")
        
        for test_case in test_cases:
            manual_id = test_case['manual_id']
            uuid = test_case['uuid']
            db_path = test_case['db_path']
            
            print(f"\n--- Manual ID: {manual_id} ---")
            print(f"DB内パス: {db_path}")
            print(f"UUID: {uuid}")
            
            # 正規化パス
            normalized_path = db_path
            if normalized_path.startswith('uploads/'):
                normalized_path = normalized_path[8:]
            if normalized_path.endswith('_mp4'):
                normalized_path = normalized_path[:-4] + '.mp4'
            
            print(f"正規化パス: {normalized_path}")
            
            # 正規化パスの存在確認
            blob = bucket.blob(normalized_path)
            exists = blob.exists()
            print(f"正規化パス存在: {'✅' if exists else '❌'}")
            
            # UUIDで始まるファイルを検索
            uuid_matches = []
            for blob_item in bucket.list_blobs(prefix="video/"):
                if uuid in blob_item.name:
                    uuid_matches.append(blob_item.name)
            
            print(f"UUID一致ファイル数: {len(uuid_matches)}")
            if uuid_matches:
                for match in uuid_matches:
                    print(f"  - {match}")
            
            # UUID部分で始まるファイルを検索
            uuid_start_matches = []
            for blob_item in bucket.list_blobs(prefix=f"video/{uuid}"):
                uuid_start_matches.append(blob_item.name)
            
            print(f"UUID開始ファイル数: {len(uuid_start_matches)}")
            if uuid_start_matches:
                for match in uuid_start_matches:
                    print(f"  - {match}")
            
            # どちらでも見つからない場合、似たパターンを検索
            if not uuid_matches and not uuid_start_matches:
                # UUIDの最初の8文字で検索
                uuid_prefix = uuid[:8]
                prefix_matches = []
                for blob_item in bucket.list_blobs(prefix="video/"):
                    if uuid_prefix in blob_item.name:
                        prefix_matches.append(blob_item.name)
                
                print(f"UUID前8文字一致ファイル数: {len(prefix_matches)}")
                if prefix_matches:
                    for match in prefix_matches[:3]:  # 最初の3個だけ表示
                        print(f"  - {match}")
                
                print(f"❌ 該当UUIDのファイルは見つかりません")
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_stage2_uuids()