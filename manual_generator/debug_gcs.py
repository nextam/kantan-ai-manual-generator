#!/usr/bin/env python3
"""GCS設定デバッグスクリプト"""

import os
from dotenv import load_dotenv

print("=== GCS設定デバッグ ===")

# .envファイルの読み込み
load_dotenv()

print(f"GOOGLE_API_KEY: {os.getenv('GOOGLE_API_KEY')[:10]}..." if os.getenv('GOOGLE_API_KEY') else "None")
print(f"GCS_BUCKET_NAME: {os.getenv('GCS_BUCKET_NAME')}")
print(f"PROJECT_ID: {os.getenv('PROJECT_ID')}")

# Google Cloud ライブラリのインポートテスト
print("\n=== Google Cloudライブラリのインポートテスト ===")
try:
    import google.generativeai as genai
    print("✅ google.generativeai インポート成功")
    HAS_GOOGLE_CLOUD = True
except ImportError as e:
    print(f"❌ google.generativeai インポート失敗: {e}")
    HAS_GOOGLE_CLOUD = False

try:
    import vertexai
    print("✅ vertexai インポート成功")
except ImportError as e:
    print(f"❌ vertexai インポート失敗: {e}")
    HAS_GOOGLE_CLOUD = False

try:
    from vertexai.generative_models import GenerativeModel
    print("✅ GenerativeModel インポート成功")
except ImportError as e:
    print(f"❌ GenerativeModel インポート失敗: {e}")
    HAS_GOOGLE_CLOUD = False

print(f"\n=== 結果 ===")
print(f"HAS_GOOGLE_CLOUD: {HAS_GOOGLE_CLOUD}")

if HAS_GOOGLE_CLOUD:
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'manual_generator')
    DEFAULT_STORAGE_TYPE = 'gcs'
    DEFAULT_STORAGE_CONFIG = {
        'bucket_name': GCS_BUCKET_NAME,
        'credentials_path': os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcp-credentials.json')
    }
    print(f"DEFAULT_STORAGE_TYPE: {DEFAULT_STORAGE_TYPE}")
    print(f"DEFAULT_STORAGE_CONFIG: {DEFAULT_STORAGE_CONFIG}")
else:
    print("ローカルストレージを使用")

# ファイルマネージャーのテスト
print("\n=== ファイルマネージャーテスト ===")
try:
    from file_manager import create_file_manager
    if HAS_GOOGLE_CLOUD:
        fm = create_file_manager(DEFAULT_STORAGE_TYPE, DEFAULT_STORAGE_CONFIG)
        print(f"✅ GCSファイルマネージャー作成成功: {type(fm)}")
        print(f"Backend type: {type(fm.backend)}")
    else:
        fm = create_file_manager('local', {'base_path': 'uploads'})
        print(f"✅ ローカルファイルマネージャー作成成功: {type(fm)}")
except Exception as e:
    print(f"❌ ファイルマネージャー作成失敗: {e}")
