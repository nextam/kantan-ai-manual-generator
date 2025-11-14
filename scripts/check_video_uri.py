"""
Check video_uri field in Manual table for debugging
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.app import app, db
from src.models.models import Manual

def check_manual_video_uri(manual_id):
    """Check video_uri for a specific manual"""
    with app.app_context():
        manual = Manual.query.get(manual_id)
        
        if not manual:
            print(f"❌ Manual ID {manual_id} not found")
            return
        
        print(f"=== Manual ID {manual_id} ===")
        print(f"Title: {manual.title}")
        print(f"video_uri: {manual.video_uri}")
        print(f"Status: {manual.generation_status}")
        print(f"Output format: {manual.output_format}")
        print(f"Created at: {manual.created_at}")
        print()
        
        # Check if it's a GCS URI
        if manual.video_uri:
            if manual.video_uri.startswith('gs://'):
                print("✅ Valid GCS URI")
            elif manual.video_uri.startswith('http'):
                print("⚠️ HTTP URL")
            else:
                print("❌ Local file path - needs GCS upload")
                print(f"Path: {manual.video_uri}")
        else:
            print("❌ No video_uri set")

if __name__ == '__main__':
    # Check manual ID 36
    check_manual_video_uri(36)
    
    # Also check recent manuals
    print("\n=== Recent Manuals ===")
    with app.app_context():
        recent_manuals = Manual.query.order_by(Manual.id.desc()).limit(5).all()
        for manual in recent_manuals:
            uri_type = "None"
            if manual.video_uri:
                if manual.video_uri.startswith('gs://'):
                    uri_type = "GCS"
                elif manual.video_uri.startswith('http'):
                    uri_type = "HTTP"
                else:
                    uri_type = "Local"
            
            print(f"ID: {manual.id} | URI Type: {uri_type} | Status: {manual.generation_status}")
