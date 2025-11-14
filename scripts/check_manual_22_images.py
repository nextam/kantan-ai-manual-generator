"""
File: check_manual_22_images.py
Purpose: Validate image extraction for Manual ID 22
"""
import sqlite3
import json

conn = sqlite3.connect(r'instance\manual_generator.db')
cursor = conn.cursor()

manual_id = 25  # Update to Manual 25

cursor.execute("""
    SELECT id, title, extracted_images, content
    FROM manuals 
    WHERE id = ?
""", (manual_id,))

row = cursor.fetchone()

if row:
    manual_id, title, extracted_images_json, content = row
    
    print(f"📋 Manual ID: {manual_id}")
    print(f"📝 Title: {title}")
    print(f"\n{'='*60}")
    
    # Check extracted_images field
    print(f"\n🖼️ extracted_images field:")
    if extracted_images_json:
        try:
            images = json.loads(extracted_images_json)
            print(f"  ✅ {len(images)} images found")
            for idx, img in enumerate(images[:3]):  # Show first 3
                img_preview = img.get('image', '')[:80] if isinstance(img, dict) else str(img)[:80]
                print(f"  [{idx+1}] {img_preview}...")
        except json.JSONDecodeError:
            print(f"  ⚠️ JSON parse error: {extracted_images_json[:100]}")
    else:
        print(f"  ❌ NULL or empty")
    
    # Check content field for frame_data
    print(f"\n📄 content field (frame_data analysis):")
    if content:
        content_str = str(content)
        if 'frame_data' in content_str:
            # Count frame_data occurrences
            frame_data_count = content_str.count('"frame_data"')
            print(f"  ℹ️ 'frame_data' appears {frame_data_count} times")
            
            # Check if image_base64 exists
            if 'image_base64' in content_str:
                image_count = content_str.count('image_base64')
                print(f"  ℹ️ 'image_base64' appears {image_count} times")
            else:
                print(f"  ⚠️ No 'image_base64' found in content")
        else:
            print(f"  ⚠️ No 'frame_data' found in content")
    else:
        print(f"  ❌ content field is NULL")
    
    print(f"\n{'='*60}")
    
    # Final verdict
    has_extracted_images = extracted_images_json is not None and len(extracted_images_json) > 10
    
    if has_extracted_images:
        print(f"\n✅ SUCCESS: Images extracted to database")
    else:
        print(f"\n❌ FAILURE: No images in extracted_images field")
        print(f"\n🔍 Debugging hints:")
        print(f"  1. Check Celery worker logs for errors")
        print(f"  2. Verify manual_tasks.py image extraction code ran")
        print(f"  3. Check if content field has frame_data with image_base64")

else:
    print(f"❌ Manual ID {manual_id} not found")

conn.close()
