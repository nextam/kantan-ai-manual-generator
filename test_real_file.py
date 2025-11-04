#!/usr/bin/env python3
import sys
import os
sys.path.append('/app')
os.chdir('/app')

from file_manager import create_file_manager
from utils.path_normalization import normalize_video_path, fix_mp4_extension

# 実際に存在するファイルでテスト
test_video_path = "video/cf7657db-dddf-4465-92de-3e31c452dbde_mp4"

print("=== Testing Real _mp4 File ===")
print(f"Input path: '{test_video_path}'")

try:
    # 正規化テスト
    canonical, candidates = normalize_video_path(test_video_path)
    print(f"Canonical path: '{canonical}'")
    print(f"All candidates: {candidates}")
    
    # ファイルマネージャーでの存在確認
    fm = create_file_manager('gcs', {
        'bucket_name': 'manual_generator',
        'credentials_path': '/app/gcp-credentials.json'
    })
    
    print(f"\n=== File Existence Test ===")
    for i, candidate in enumerate(candidates):
        exists = fm.file_exists(candidate)
        print(f"  {i+1}. '{candidate}' -> exists: {exists}")
        
    print(f"\n=== Testing our modification ===")
    # 修正前の動作（直接バックエンド）
    backend_original = fm.backend.file_exists(test_video_path)
    backend_fixed = fm.backend.file_exists(canonical)
    print(f"Backend direct - original: {backend_original}, fixed: {backend_fixed}")
    
    # 修正後の動作（file_manager経由）
    fm_result = fm.file_exists(test_video_path)
    print(f"FileManager.file_exists('{test_video_path}') -> {fm_result}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()