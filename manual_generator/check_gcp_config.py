#!/usr/bin/env python3
"""
Google Cloud認証情報の設定確認スクリプト
"""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

def main():
    print("=== Google Cloud 認証設定確認 ===\n")
    
    # .envファイルの読み込み
    load_dotenv()
    print(f"✅ .envファイル読み込み完了")
    
    # 環境変数の確認
    print("\n--- 環境変数 ---")
    env_vars = [
        'GOOGLE_APPLICATION_CREDENTIALS',
        'GOOGLE_CLOUD_PROJECT_ID',
        'GOOGLE_API_KEY',
        'GCS_BUCKET_NAME',
        'PROJECT_ID'
    ]
    
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # APIキーは一部のみ表示
            if 'KEY' in var and len(value) > 10:
                display_value = f"{value[:10]}...{value[-4:]}"
            else:
                display_value = value
            print(f"  {var}: {display_value}")
        else:
            print(f"  {var}: ❌ 未設定")
    
    # 認証ファイルの確認
    print("\n--- 認証ファイル ---")
    creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
    
    if creds_path:
        # 相対パスの場合は絶対パスに変換
        if not os.path.isabs(creds_path):
            abs_creds_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), creds_path)
        else:
            abs_creds_path = creds_path
        
        print(f"  認証ファイルパス: {abs_creds_path}")
        
        if os.path.exists(abs_creds_path):
            print("  ✅ ファイル存在: OK")
            
            # JSONファイルの内容確認
            try:
                with open(abs_creds_path, 'r') as f:
                    creds_data = json.load(f)
                
                print(f"  📝 サービスアカウント情報:")
                print(f"    - Project ID: {creds_data.get('project_id')}")
                print(f"    - Client Email: {creds_data.get('client_email')}")
                print(f"    - Type: {creds_data.get('type')}")
                
                # プロジェクトIDの整合性確認
                env_project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
                creds_project_id = creds_data.get('project_id')
                
                if env_project_id == creds_project_id:
                    print("  ✅ プロジェクトID整合性: OK")
                else:
                    print(f"  ⚠️  プロジェクトID不整合:")
                    print(f"    環境変数: {env_project_id}")
                    print(f"    認証ファイル: {creds_project_id}")
                    
            except json.JSONDecodeError:
                print("  ❌ JSONファイル形式エラー")
            except Exception as e:
                print(f"  ❌ ファイル読み込みエラー: {e}")
        else:
            print("  ❌ ファイル存在: NG")
            print(f"    指定されたパスにファイルが見つかりません")
    else:
        print("  ❌ 認証ファイルパスが設定されていません")
    
    # 推奨設定の表示
    print("\n--- 推奨設定 ---")
    print("  .envファイルに以下の設定を追加してください:")
    print("")
    print("  GOOGLE_APPLICATION_CREDENTIALS=gcp-credentials.json")
    print("  GOOGLE_CLOUD_PROJECT_ID=career-survival")
    print("  GOOGLE_API_KEY=your_api_key_here")
    print("  GCS_BUCKET_NAME=manual_generator")
    print("  PROJECT_ID=career-survival")
    print("")
    print("  認証ファイル 'gcp-credentials.json' をプロジェクトルートに配置してください。")

if __name__ == "__main__":
    main()
