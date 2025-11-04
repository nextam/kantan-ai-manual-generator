#!/usr/bin/env python3
"""
正規化後のパスがGCSに存在するか確認するスクリプト
"""

from google.cloud import storage
import json

def check_normalized_path():
    try:
        # GCSクライアント初期化
        client = storage.Client.from_service_account_json("/app/gcp-credentials.json")
        bucket = client.bucket("manual_generator")
        
        # Manual ID 57の正規化後パス
        normalized_path = "video/5b611bba-c700-478c-882f-238b7bd11ae8.mp4"
        
        # ファイルの存在確認
        blob = bucket.blob(normalized_path)
        exists = blob.exists()
        
        print(f"=== Manual ID 57 正規化後パス確認 ===")
        print(f"正規化後パス: {normalized_path}")
        print(f"GCS存在確認: {exists}")
        
        if exists:
            print(f"ファイルサイズ: {blob.size} bytes")
            print(f"更新日時: {blob.updated}")
        else:
            # 似たような名前のファイルを検索
            print("\n=== 類似ファイル検索 ===")
            similar_files = []
            for blob_item in bucket.list_blobs(prefix="video/"):
                if "5b611bba-c700-478c-882f-238b7bd11ae8" in blob_item.name:
                    similar_files.append(blob_item.name)
                    print(f"類似ファイル: {blob_item.name}")
            
            if not similar_files:
                print("類似ファイルが見つかりません")
        
        return exists
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return False

if __name__ == "__main__":
    check_normalized_path()