"""
File: check_manual_44_sources.py
Purpose: Check source video information for manual ID 44
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.app import app
from src.models.models import Manual, ManualSourceFile, UploadedFile

with app.app_context():
    manual = Manual.query.get(44)
    if not manual:
        print("Manual ID 44 not found")
        sys.exit(1)
    
    print(f"=== Manual ID {manual.id} ===")
    print(f"Title: {manual.title}")
    print(f"Manual Type: {manual.manual_type}")
    print(f"Output Format: {manual.output_format}")
    print(f"Content Video URI: {manual.content_video_uri}")
    print()
    
    # Check ManualSourceFile records
    source_files = ManualSourceFile.query.filter_by(manual_id=manual.id).all()
    print(f"=== ManualSourceFile Records: {len(source_files)} ===")
    for sf in source_files:
        print(f"  ID: {sf.id}, File ID: {sf.file_id}, Role: {sf.role}")
        if sf.file_id:
            file = UploadedFile.query.get(sf.file_id)
            if file:
                print(f"    Filename: {file.original_filename}")
                print(f"    Path: {file.file_path}")
                print(f"    Type: {file.file_type}")
    print()
    
    # Test to_dict_with_sources()
    manual_dict = manual.to_dict_with_sources()
    print(f"=== to_dict_with_sources() Result ===")
    print(f"source_videos length: {len(manual_dict.get('source_videos', []))}")
    for sv in manual_dict.get('source_videos', []):
        print(f"  File ID: {sv.get('file_id')}")
        print(f"  Role: {sv.get('role')}")
        print(f"  Type: {sv.get('type')}")
        print(f"  Filename: {sv.get('filename')}")
        print(f"  URL: {sv.get('url')}")
        print()
