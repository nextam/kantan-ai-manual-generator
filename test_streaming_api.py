#!/usr/bin/env python3
import sys
sys.path.append('/app')

# 実際の動画ストリーミングAPIのパス正規化処理をテスト
from utils.path_normalization import normalize_video_path

test_video_path = "video/5b611bba-c700-478c-882f-238b7bd11ae8_mp4"

print("=== Video Path Normalization Test ===")
print(f"Input path: '{test_video_path}'")

try:
    canonical, candidates = normalize_video_path(test_video_path)
    print(f"Canonical path: '{canonical}'")
    print(f"All candidates: {candidates}")
    
    # file_manager での存在確認もテスト
    from file_manager import get_file_manager
    fm = get_file_manager()
    
    print(f"\n=== File Existence Test ===")
    for i, candidate in enumerate(candidates):
        exists = fm.file_exists(candidate)
        print(f"  {i+1}. '{candidate}' -> exists: {exists}")
        
    print(f"\n=== Final existence check ===")
    final_exists = fm.file_exists(test_video_path)
    print(f"Original path '{test_video_path}' -> exists: {final_exists}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()