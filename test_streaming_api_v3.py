#!/usr/bin/env python3
import sys
import os
sys.path.append('/app')
os.chdir('/app')

from file_manager import create_file_manager, FileManager
from utils.path_normalization import normalize_video_path

test_video_path = "video/5b611bba-c700-478c-882f-238b7bd11ae8_mp4"

print("=== Video Path Normalization Test ===")
print(f"Input path: '{test_video_path}'")

try:
    canonical, candidates = normalize_video_path(test_video_path)
    print(f"Canonical path: '{canonical}'")
    print(f"All candidates: {candidates}")
    
    # file_manager での存在確認もテスト
    # デフォルトのファイルマネージャーを作成（GCS使用）
    fm = create_file_manager('gcs', {
        'bucket_name': 'manual_generator',
        'credentials_path': '/app/gcp-credentials.json'
    })
    
    print(f"\n=== File Existence Test ===")
    for i, candidate in enumerate(candidates):
        exists = fm.file_exists(candidate)
        print(f"  {i+1}. '{candidate}' -> exists: {exists}")
        
    print(f"\n=== Final existence check ===")
    final_exists = fm.file_exists(test_video_path)
    print(f"Original path '{test_video_path}' -> exists: {final_exists}")
    
    # 修正版file_existsのテスト
    print(f"\n=== Testing modified file_exists behavior ===")
    # オリジナルのバックエンドで直接チェック
    backend_exists_original = fm.backend.file_exists(test_video_path)
    backend_exists_fixed = fm.backend.file_exists(canonical)
    print(f"Backend direct check - original: {backend_exists_original}, fixed: {backend_exists_fixed}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()