#!/usr/bin/env python3
"""
stage2_contentの構造詳細確認
"""

import sqlite3
import json
import sys
import os
sys.path.append('/app')

def analyze_stage2_content():
    try:
        # データベース接続
        db_path = '/app/instance/manual_generator.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # stage2_contentがあるマニュアルを取得
        cursor.execute("""
            SELECT id, title, stage2_content 
            FROM manuals 
            WHERE stage2_content IS NOT NULL 
            AND stage2_content != '' 
            ORDER BY id DESC
            LIMIT 5
        """)
        
        manuals = cursor.fetchall()
        print(f"=== stage2_content構造分析（最新5件）===")
        
        for manual_id, title, stage2_content in manuals:
            print(f"\n--- Manual ID: {manual_id} ---")
            print(f"タイトル: {title}")
            print(f"stage2_content長: {len(stage2_content)} 文字")
            
            try:
                content_data = json.loads(stage2_content)
                print(f"JSON構造:")
                
                # トップレベルのキー確認
                top_keys = list(content_data.keys())
                print(f"  トップレベルキー: {top_keys}")
                
                # steps構造確認
                if 'steps' in content_data:
                    steps = content_data['steps']
                    print(f"  ステップ数: {len(steps)}")
                    
                    # 最初のステップの構造を詳しく見る
                    if steps:
                        first_step = steps[0]
                        step_keys = list(first_step.keys())
                        print(f"  ステップキー: {step_keys}")
                        
                        # 動画関連の情報を探す
                        for key in step_keys:
                            if 'video' in key.lower() or 'Video' in key:
                                print(f"    {key}: {first_step[key]}")
                
                # その他のキーで動画情報を探す
                for key, value in content_data.items():
                    if 'video' in key.lower() or 'Video' in key:
                        print(f"  {key}: {value}")
                
                # JSONの一部を表示（最初の500文字）
                json_preview = json.dumps(content_data, ensure_ascii=False)[:500]
                print(f"  JSON preview: {json_preview}...")
                
            except json.JSONDecodeError as e:
                print(f"  JSONパース失敗: {e}")
                # 生テキストの最初の200文字を表示
                print(f"  生テキスト: {stage2_content[:200]}...")
            except Exception as e:
                print(f"  エラー: {e}")
        
        conn.close()
        
        # さらに動画パスが含まれているマニュアルを直接検索
        print(f"\n=== 動画パス直接検索 ===")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, title 
            FROM manuals 
            WHERE stage2_content LIKE '%uploads/video%' 
            OR stage2_content LIKE '%gs://manual_generator%'
            OR stage2_content LIKE '%.mp4%'
            OR stage2_content LIKE '%_mp4%'
            LIMIT 5
        """)
        
        video_manuals = cursor.fetchall()
        print(f"動画パスを含むマニュアル: {len(video_manuals)}件")
        for manual_id, title in video_manuals:
            print(f"  Manual ID: {manual_id}, タイトル: {title}")
        
        conn.close()
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_stage2_content()