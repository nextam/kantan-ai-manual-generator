"""
Manual ID 18 の画像データを確認するスクリプト
"""
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app
from src.models.models import db, Manual
import json

def check_manual_images(manual_id=18):
    with app.app_context():
        manual = Manual.query.get(manual_id)
        
        if not manual:
            print(f"❌ Manual ID {manual_id} が見つかりません")
            return
        
        print("=" * 80)
        print(f"📋 Manual ID: {manual.id}")
        print(f"📝 Title: {manual.title}")
        print(f"🏷️  Type: {manual.manual_type}")
        print(f"📊 Output Format: {manual.output_format}")
        print(f"✅ Status: {manual.generation_status}")
        print("=" * 80)
        
        # content フィールドを確認
        print("\n📄 Content Field:")
        if manual.content:
            try:
                # Python辞書形式の文字列をパース
                content_str = manual.content.replace("'", '"').replace('None', 'null').replace('True', 'true').replace('False', 'false')
                content_dict = json.loads(content_str)
                
                print(f"  - Type: dict")
                print(f"  - Keys: {list(content_dict.keys())}")
                
                if 'analysis_result' in content_dict:
                    analysis = content_dict['analysis_result']
                    print(f"\n  📊 Analysis Result:")
                    print(f"    - Title: {analysis.get('title', 'N/A')}")
                    print(f"    - Steps: {len(analysis.get('steps', []))}")
                    
                    # frame_index と frame_data をチェック
                    for step in analysis.get('steps', []):
                        frame_idx = step.get('frame_index')
                        frame_data = step.get('frame_data')
                        print(f"    - Step {step['step_number']}: frame_index={frame_idx}, frame_data={'あり' if frame_data else 'なし'}")
                
            except Exception as e:
                print(f"  ❌ Parse error: {e}")
                print(f"  Raw: {manual.content[:200]}...")
        else:
            print("  ⚠️  Content is NULL")
        
        # extracted_images フィールドを確認
        print("\n🖼️  Extracted Images Field:")
        if manual.extracted_images:
            try:
                images = json.loads(manual.extracted_images)
                print(f"  - Count: {len(images)}")
                for idx, img in enumerate(images):
                    print(f"  - Image {idx + 1}: {img.get('step_title', 'N/A')} (URI: {img.get('image_uri', 'N/A')[:50]}...)")
            except Exception as e:
                print(f"  ❌ Parse error: {e}")
        else:
            print("  ⚠️  Extracted Images is NULL or empty")
        
        # Stage content を確認
        print("\n📑 Stage Content:")
        print(f"  - Stage1: {'あり' if manual.stage1_content else 'なし'}")
        print(f"  - Stage2: {'あり' if manual.stage2_content else 'なし'}")
        print(f"  - Stage3: {'あり' if manual.stage3_content else 'なし'}")
        
        # Phase 6 フィールドを確認
        print("\n📦 Phase 6 Multi-Format Fields:")
        print(f"  - content_html: {'あり' if manual.content_html else 'なし'}")
        print(f"  - content_text: {'あり' if manual.content_text else 'なし'}")
        print(f"  - content_video_uri: {'あり' if manual.content_video_uri else 'なし'}")
        print(f"  - video_clips: {len(manual.get_video_clips()) if manual.get_video_clips() else 0}")
        print(f"  - subtitles_data: {len(manual.get_subtitles_data()) if manual.get_subtitles_data() else 0}")

if __name__ == '__main__':
    import sys
    manual_id = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    check_manual_images(manual_id)
