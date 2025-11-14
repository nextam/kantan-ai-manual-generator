"""
Check manual images without verbose logging
"""
import sys
import os
from pathlib import Path

# Suppress Flask app logs
os.environ['WERKZEUG_RUN_MAIN'] = 'true'

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Suppress all logging before imports
import logging
logging.disable(logging.CRITICAL)

from src.models.models import Manual
from src.core.app import db, app
import json

def check_manual_images(manual_id=None):
    """Check manual images in database"""
    
    # Get manual from database
    if manual_id:
        manual = Manual.query.get(manual_id)
    else:
        manual = Manual.query.order_by(Manual.id.desc()).first()
    
    if not manual:
        print(f"❌ No manual found")
        return
    
    print("=" * 60)
    print(f"MANUAL {manual.id} IMAGE CHECK")
    print("=" * 60)
    print(f"\n✅ Manual: {manual.title}")
    print(f"   Output format: {manual.output_format}")
    print(f"   Manual type: {manual.manual_type}")
    
    # Check extracted_images field
    print(f"\n📊 Database Field 'extracted_images':")
    print(f"   Type: {type(manual.extracted_images)}")
    print(f"   Value: {manual.extracted_images}")
    
    if manual.extracted_images:
        if isinstance(manual.extracted_images, str):
            try:
                images = json.loads(manual.extracted_images)
                print(f"   ✅ Parsed as JSON: {len(images)} images")
                if images:
                    print(f"\n   First image sample:")
                    first = images[0]
                    for key in ['gcs_uri', 'filename', 'timestamp', 'frame_index']:
                        if key in first:
                            print(f"      {key}: {first[key]}")
            except Exception as e:
                print(f"   ❌ Failed to parse JSON: {e}")
        elif isinstance(manual.extracted_images, list):
            print(f"   ✅ Already a list: {len(manual.extracted_images)} images")
            if manual.extracted_images:
                print(f"\n   First image sample:")
                first = manual.extracted_images[0]
                for key in ['gcs_uri', 'filename', 'timestamp', 'frame_index']:
                    if key in first:
                        print(f"      {key}: {first[key]}")
    else:
        print(f"   ⚠️ EMPTY or None")
    
    # Check to_dict() output
    print(f"\n📤 API Response (to_dict()):")
    manual_dict = manual.to_dict()
    extracted = manual_dict.get('extracted_images')
    print(f"   Type: {type(extracted)}")
    print(f"   Value: {extracted}")
    
    if extracted and len(extracted) > 0:
        print(f"   ✅ {len(extracted)} images in API response")
        print(f"   First image keys: {list(extracted[0].keys())}")
    else:
        print(f"   ❌ EMPTY in API response")
    
    # Check content for image placeholders
    print(f"\n🔍 Content Analysis:")
    content = manual.content or manual.content_html or ""
    
    placeholders = {
        "[ここに、": 0,
        "の写真]": 0,
        "の画像]": 0,
        "<img": 0
    }
    
    for placeholder in placeholders:
        placeholders[placeholder] = content.count(placeholder)
    
    for placeholder, count in placeholders.items():
        if count > 0:
            symbol = "📷" if count > 0 and placeholder != "<img" else "🖼️"
            print(f"   {symbol} '{placeholder}': {count} times")
    
    if all(c == 0 for c in placeholders.values()):
        print(f"   ℹ️ No image placeholders or tags found")
    
    print("\n" + "=" * 60)
    
    # Summary
    has_db_images = bool(manual.extracted_images and len(manual.extracted_images) > 0)
    has_api_images = bool(extracted and len(extracted) > 0)
    has_placeholders = placeholders["[ここに、"] > 0 or placeholders["の写真]"] > 0
    
    print("\n📋 SUMMARY:")
    print(f"   Database has images: {'✅ YES' if has_db_images else '❌ NO'}")
    print(f"   API returns images: {'✅ YES' if has_api_images else '❌ NO'}")
    print(f"   Content has placeholders: {'✅ YES' if has_placeholders else '❌ NO'}")
    
    if not has_db_images:
        print(f"\n⚠️ ROOT CAUSE: No images in database 'extracted_images' field")
        print(f"   This means image extraction during manual generation failed or was skipped.")

if __name__ == '__main__':
    with app.app_context():
        if len(sys.argv) > 1:
            try:
                manual_id = int(sys.argv[1])
                check_manual_images(manual_id)
            except ValueError:
                print(f"Invalid manual ID: {sys.argv[1]}")
        else:
            # Check latest manual
            check_manual_images()
