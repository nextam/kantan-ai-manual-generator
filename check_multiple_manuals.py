#!/usr/bin/env python3
"""
データベースの複数マニュアルのファイル存在確認
"""

import sqlite3
import json
from google.cloud import storage
import sys
import os
sys.path.append('/app')

def check_multiple_manual_files():
    try:
        # データベース接続
        db_path = '/app/instance/manual_generator.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # GCSクライアント初期化
        gcs_client = storage.Client.from_service_account_json("/app/gcp-credentials.json")
        bucket = gcs_client.bucket("manual_generator")
        
        # stage2_contentにvideo情報があるマニュアルを取得（最大10個）
        cursor.execute("""
            SELECT id, title, stage2_content 
            FROM manuals 
            WHERE stage2_content IS NOT NULL 
            AND stage2_content != '' 
            AND stage2_content LIKE '%video%'
            LIMIT 10
        """)
        
        manuals = cursor.fetchall()
        print(f"=== 動画付きマニュアル検証（{len(manuals)}件）===")
        
        for manual_id, title, stage2_content in manuals:
            print(f"\n--- Manual ID: {manual_id} ---")
            print(f"タイトル: {title}")
            
            try:
                content_data = json.loads(stage2_content)
                video_paths = []
                
                # 各ステップの動画パスを収集
                for step in content_data.get('steps', []):
                    expert_video = step.get('expertVideo', {}).get('path')
                    novice_video = step.get('noviceVideo', {}).get('path')
                    
                    if expert_video:
                        video_paths.append(('expert', expert_video))
                    if novice_video:
                        video_paths.append(('novice', novice_video))
                
                print(f"動画ファイル数: {len(video_paths)}")
                
                for video_type, video_path in video_paths:
                    print(f"  {video_type}: {video_path}")
                    
                    # パス正規化（簡易版）
                    normalized_path = video_path
                    if normalized_path.startswith('gs://'):
                        parts = normalized_path[5:].split('/', 1)
                        if len(parts) > 1:
                            normalized_path = parts[1]
                    
                    if normalized_path.startswith('uploads/'):
                        normalized_path = normalized_path[8:]
                    
                    if normalized_path.endswith('_mp4'):
                        normalized_path = normalized_path[:-4] + '.mp4'
                    
                    # GCSファイル存在確認
                    blob = bucket.blob(normalized_path)
                    exists = blob.exists()
                    print(f"    正規化後: {normalized_path}")
                    print(f"    GCS存在: {'✅' if exists else '❌'}")
                    
                    # UUIDを抽出してマッチするファイルを検索
                    if not exists:
                        # UUIDパターンを抽出
                        import re
                        uuid_pattern = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'
                        uuid_match = re.search(uuid_pattern, video_path)
                        
                        if uuid_match:
                            target_uuid = uuid_match.group(1)
                            print(f"    UUID: {target_uuid}")
                            
                            # GCSで同じUUIDを含むファイルを検索
                            similar_files = []
                            for blob in bucket.list_blobs(prefix="video/"):
                                if target_uuid in blob.name:
                                    similar_files.append(blob.name)
                            
                            if similar_files:
                                print(f"    類似ファイル: {similar_files[0]}")
                            else:
                                print(f"    類似ファイル: なし")
            
            except json.JSONDecodeError:
                print("  JSONパース失敗")
            except Exception as e:
                print(f"  エラー: {e}")
        
        conn.close()
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_multiple_manual_files()