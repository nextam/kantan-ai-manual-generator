#!/usr/bin/env python3
import sys
sys.path.append('/app')

try:
    from utils.path_normalization import fix_mp4_extension
    print("✓ fix_mp4_extension imported successfully")
    
    # テストケース
    test_result = fix_mp4_extension("video/5b611bba-c700-478c-882f-238b7bd11ae8_mp4")
    print(f"Test result: '{test_result}'")
    
    # 実際の問題ファイルもテスト
    test_url = "video%2F5b611bba-c700-478c-882f-238b7bd11ae8_mp4"
    from urllib.parse import unquote
    decoded = unquote(test_url)
    fixed = fix_mp4_extension(decoded)
    print(f"URL decoded and fixed: '{test_url}' -> '{decoded}' -> '{fixed}'")
    
except ImportError as e:
    print(f"✗ Import failed: {e}")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()