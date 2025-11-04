#!/usr/bin/env python3
import sys
import os
sys.path.append('/app')
os.chdir('/app')

from google.cloud import storage

# GCSで実際のファイル名をチェック
try:
    client = storage.Client.from_service_account_json('/app/gcp-credentials.json')
    bucket = client.bucket('manual_generator')
    
    print("=== GCS Files starting with 5b611bba ===")
    blobs = bucket.list_blobs(prefix='video/5b611bba')
    
    for blob in blobs:
        print(f"Found: {blob.name}")
        
    print("\n=== Check specific patterns ===")
    # 各パターンをチェック
    test_patterns = [
        'video/5b611bba-c700-478c-882f-238b7bd11ae8_mp4',
        'video/5b611bba-c700-478c-882f-238b7bd11ae8.mp4',
        'video/5b611bba-c700-478c-882f-238b7bd11ae8_____mp4',
    ]
    
    for pattern in test_patterns:
        blob = bucket.blob(pattern)
        exists = blob.exists()
        print(f"  '{pattern}' -> exists: {exists}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()