"""
Check manual images in database and API response
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.models.models import Manual
from src.core.app import db
import json

def check_manual_images(manual_id):
    """Check manual images in database"""
    print("=" * 60)
    print(f"MANUAL {manual_id} IMAGE CHECK")
    print("=" * 60)
    
    # Get manual from database
    manual = Manual.query.get(manual_id)
    
    if not manual:
        print(f"❌ Manual {manual_id} not found")
        return
    
    print(f"\n✅ Manual found: {manual.title}")
    print(f"   Output format: {manual.output_format}")
    print(f"   Manual type: {manual.manual_type}")
    print(f"   Created: {manual.created_at}")
    
    # Check extracted_images field
    print(f"\n📊 Database Fields:")
    print(f"   extracted_images type: {type(manual.extracted_images)}")
    print(f"   extracted_images value: {manual.extracted_images}")
    
    if manual.extracted_images:
        if isinstance(manual.extracted_images, str):
            try:
                images = json.loads(manual.extracted_images)
                print(f"   Parsed images count: {len(images)}")
                if images:
                    print(f"   First image: {images[0]}")
            except:
                print(f"   ❌ Failed to parse JSON")
        elif isinstance(manual.extracted_images, list):
            print(f"   Images count: {len(manual.extracted_images)}")
            if manual.extracted_images:
                print(f"   First image: {manual.extracted_images[0]}")
    else:
        print(f"   ⚠️ extracted_images is empty or None")
    
    # Check to_dict() output
    print(f"\n📤 API Response (to_dict()):")
    manual_dict = manual.to_dict()
    print(f"   extracted_images in dict: {manual_dict.get('extracted_images')}")
    print(f"   extracted_images type: {type(manual_dict.get('extracted_images'))}")
    
    if manual_dict.get('extracted_images'):
        print(f"   Count: {len(manual_dict['extracted_images'])}")
        if manual_dict['extracted_images']:
            print(f"   First image keys: {list(manual_dict['extracted_images'][0].keys())}")
    
    # Check content for image placeholders
    print(f"\n🔍 Content Analysis:")
    content = manual.content or manual.content_html or ""
    image_placeholders = [
        "[ここに、",
        "[画像:",
        "の写真]",
        "の画像]"
    ]
    
    for placeholder in image_placeholders:
        count = content.count(placeholder)
        if count > 0:
            print(f"   Found '{placeholder}': {count} times")
    
    # Check if content contains actual image tags
    img_tags = content.count("<img")
    print(f"   <img> tags: {img_tags}")
    
    print("\n" + "=" * 60)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_manual_images.py <manual_id>")
        sys.exit(1)
    
    manual_id = int(sys.argv[1])
    
    # Initialize Flask app context
    from src.core.app import app
    with app.app_context():
        check_manual_images(manual_id)
