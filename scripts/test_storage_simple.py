#!/usr/bin/env python3
import os
import sys
sys.path.append('/app')

def test_storage_config():
    """ストレージ設定をテスト"""
    try:
        print("=== ストレージ設定テスト ===")
        
        from app import HAS_GOOGLE_CLOUD, DEFAULT_STORAGE_TYPE, DEFAULT_STORAGE_CONFIG
        
        print(f"HAS_GOOGLE_CLOUD: {HAS_GOOGLE_CLOUD}")
        print(f"DEFAULT_STORAGE_TYPE: {DEFAULT_STORAGE_TYPE}")
        print(f"DEFAULT_STORAGE_CONFIG: {DEFAULT_STORAGE_CONFIG}")
        
        if DEFAULT_STORAGE_TYPE == 'gcs':
            print("✅ デフォルトストレージがGCSに設定されています")
            bucket_name = DEFAULT_STORAGE_CONFIG.get('bucket_name')
            print(f"📦 使用バケット: {bucket_name}")
        else:
            print("⚠️ デフォルトストレージがローカルです")
            
        # ファイルマネージャー作成テスト（認証なし）
        print("\n=== ファイルマネージャー作成テスト ===")
        from file_manager import create_file_manager
        
        if HAS_GOOGLE_CLOUD:
            fm = create_file_manager('gcs', DEFAULT_STORAGE_CONFIG)
            print(f"GCSファイルマネージャー作成成功: {type(fm)}")
            print(f"バックエンドタイプ: {type(fm.backend)}")
            if hasattr(fm.backend, 'bucket_name'):
                print(f"GCSバケット: {fm.backend.bucket_name}")
        else:
            print("Google Cloud無効環境")
            
    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_storage_config()