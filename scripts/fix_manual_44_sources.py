"""
File: fix_manual_44_sources.py
Purpose: Add ManualSourceFile record for manual ID 44
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.core.app import app, db
from src.models.models import Manual, ManualSourceFile, UploadedFile

with app.app_context():
    manual = Manual.query.get(44)
    if not manual:
        print("Manual ID 44 not found")
        sys.exit(1)
    
    print(f"=== Manual ID {manual.id}: {manual.title} ===")
    print(f"Content Video URI: {manual.content_video_uri}")
    
    # Find the uploaded file with matching path
    # Check both content_video_uri and content field
    content_to_check = manual.content_video_uri or manual.content
    if content_to_check:
        # Extract GCS path from content
        import re
        # Look for gs:// URLs in content
        gs_urls = re.findall(r'gs://[^\s"\'<>]+', content_to_check)
        if gs_urls:
            print(f"\nFound {len(gs_urls)} GCS URLs in content")
            for url in gs_urls[:3]:  # Show first 3
                print(f"  {url}")
            
            # Try to find matching uploaded file
            base_url = gs_urls[0].split('#')[0]  # Remove fragment
            print(f"\nSearching for file with path: {base_url}")
            
            # Search by both full gs:// URL and relative path
            uploaded_file = UploadedFile.query.filter(
                (UploadedFile.file_path == base_url) |
                (UploadedFile.file_path.like(f"%{base_url.split('/')[-1]}%"))
            ).first()
            
            if not uploaded_file:
                # Try searching by original filename from GCS path
                filename_from_url = base_url.split('/')[-1].split('_', 1)[-1] if '_' in base_url.split('/')[-1] else base_url.split('/')[-1]
                print(f"Trying filename match: {filename_from_url}")
                uploaded_file = UploadedFile.query.filter(
                    UploadedFile.original_filename.like(f"%{filename_from_url}%")
                ).first()
            
            if uploaded_file:
                print(f"Found uploaded file: ID={uploaded_file.id}, {uploaded_file.original_filename}")
                
                # Check if ManualSourceFile already exists
                existing = ManualSourceFile.query.filter_by(
                    manual_id=manual.id,
                    file_id=uploaded_file.id
                ).first()
                
                if existing:
                    print(f"ManualSourceFile already exists: ID={existing.id}")
                else:
                    # Create new ManualSourceFile record
                    source_file = ManualSourceFile(
                        manual_id=manual.id,
                        file_id=uploaded_file.id,
                        role='primary'  # or 'expert'
                    )
                    db.session.add(source_file)
                    db.session.commit()
                    print(f"✅ Created ManualSourceFile record: ID={source_file.id}")
            else:
                print(f"❌ No uploaded file found with path: {base_url}")
                print("\nSearching all uploaded files...")
                all_files = UploadedFile.query.filter(
                    UploadedFile.company_id == manual.company_id
                ).order_by(UploadedFile.id.desc()).limit(10).all()
                print(f"Recent uploaded files (last 10):")
                for f in all_files:
                    print(f"  ID={f.id}: {f.original_filename}")
                    print(f"    Path: {f.file_path}")
        else:
            print("❌ No gs:// URLs found in manual content")
    else:
        print("❌ No content_video_uri set")
