"""
Test text_with_images manual generation workflow
"""
import sys
import os
from pathlib import Path

# Suppress logging
os.environ['WERKZEUG_RUN_MAIN'] = 'true'
import logging
logging.disable(logging.CRITICAL)

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.models import Manual, ManualTemplate, User, Company
from src.core.app import app, db
import json
from datetime import datetime

def test_text_with_images_workflow():
    """Test the complete text_with_images workflow"""
    
    with app.app_context():
        print("=" * 70)
        print("TEXT_WITH_IMAGES WORKFLOW TEST")
        print("=" * 70)
        
        # Check if we have any manuals with text_with_images format
        manual = Manual.query.filter_by(output_format='text_with_images').order_by(Manual.id.desc()).first()
        
        if not manual:
            print("\n❌ No manuals found with output_format='text_with_images'")
            print("\nTo test, create a manual with:")
            print("  - Output format: text_with_images")
            print("  - Video uploaded")
            return
        
        print(f"\n✅ Found manual: {manual.title} (ID: {manual.id})")
        print(f"   Status: {manual.generation_status}")
        print(f"   Output format: {manual.output_format}")
        print(f"   Created: {manual.created_at}")
        
        # Check extracted_images field in database
        print(f"\n📊 Database Check:")
        print(f"   extracted_images (raw): {type(manual.extracted_images)}")
        if manual.extracted_images:
            print(f"   Length: {len(manual.extracted_images)} chars")
            try:
                images = json.loads(manual.extracted_images)
                print(f"   ✅ Parsed as JSON: {len(images)} images")
                if images:
                    print(f"\n   First image sample:")
                    first = images[0]
                    for key in ['step_number', 'step_title', 'timestamp', 'gcs_uri', 'image']:
                        if key in first:
                            value = first[key]
                            if key == 'image' and value:
                                print(f"      {key}: {value[:50]}... (truncated)")
                            else:
                                print(f"      {key}: {value}")
            except Exception as e:
                print(f"   ❌ Failed to parse: {e}")
        else:
            print(f"   ⚠️ EMPTY")
        
        # Check API response
        print(f"\n📤 API Response Check:")
        manual_dict = manual.to_dict()
        extracted = manual_dict.get('extracted_images')
        print(f"   Type: {type(extracted)}")
        print(f"   Value: {extracted is not None}")
        
        if extracted:
            print(f"   ✅ {len(extracted)} images in response")
            if extracted:
                first = extracted[0]
                print(f"\n   First image keys: {list(first.keys())}")
                for key, value in first.items():
                    if key == 'image' and value:
                        print(f"      {key}: {value[:50]}... (truncated)")
                    else:
                        print(f"      {key}: {value}")
        else:
            print(f"   ❌ NO IMAGES")
        
        # Check content for placeholders
        print(f"\n🔍 Content Check:")
        content = manual.content or ""
        placeholders = {
            "[ここに、": content.count("[ここに、"),
            "の写真]": content.count("の写真]"),
            "<img": content.count("<img")
        }
        
        for placeholder, count in placeholders.items():
            if count > 0:
                print(f"   '{placeholder}': {count} times")
        
        # Summary
        print(f"\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        
        has_db_images = bool(manual.extracted_images)
        has_api_images = bool(extracted)
        has_placeholders = placeholders["[ここに、"] > 0
        
        print(f"✓ Database has images: {'✅ YES' if has_db_images else '❌ NO'}")
        print(f"✓ API returns images: {'✅ YES' if has_api_images else '❌ NO'}")
        print(f"✓ Content has placeholders: {'✅ YES' if has_placeholders else 'ℹ️ NO'}")
        
        if not has_db_images or not has_api_images:
            print(f"\n⚠️ ISSUE DETECTED:")
            if not has_db_images:
                print(f"   - Images not saved to database during generation")
                print(f"   - Check Celery task logs for image extraction errors")
            if not has_api_images:
                print(f"   - API not returning images (check Manual.to_dict())")
        else:
            print(f"\n✅ ALL CHECKS PASSED - Images should display in UI")

if __name__ == '__main__':
    test_text_with_images_workflow()
