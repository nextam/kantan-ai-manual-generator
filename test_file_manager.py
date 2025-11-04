#!/usr/bin/env python3
import os
import sys
sys.path.append('/app')

def test_file_manager_selection():
    """ファイルマネージャーの選択をテスト"""
    try:
        print("=== ファイルマネージャー選択テスト ===")
        
        # アプリケーションコンテキストでテスト
        from app import app, get_file_manager
        
        with app.app_context():
            # ファイルマネージャーを取得
            fm = get_file_manager()
            
            print(f"ファイルマネージャータイプ: {type(fm)}")
            print(f"バックエンドタイプ: {type(fm.backend)}")
            
            # バックエンドの設定確認
            if hasattr(fm.backend, 'bucket_name'):
                print(f"GCSバケット名: {fm.backend.bucket_name}")
                print("✅ GCSファイルマネージャーが選択されました")
            elif hasattr(fm.backend, 'base_path'):
                print(f"ローカルベースパス: {fm.backend.base_path}")
                print("⚠️ ローカルファイルマネージャーが選択されました")
            
    except Exception as e:
        print(f"テストエラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_file_manager_selection()