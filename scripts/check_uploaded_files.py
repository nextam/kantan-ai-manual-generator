"""
Check uploaded files table for GCS URIs
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.app import app, db
from src.models.models import UploadedFile

def check_uploaded_files():
    """Check recent uploaded files"""
    with app.app_context():
        recent_files = UploadedFile.query.order_by(UploadedFile.id.desc()).limit(10).all()
        
        print("=== Recent Uploaded Files ===\n")
        
        for file in recent_files:
            print(f"ID: {file.id}")
            print(f"Original filename: {file.original_filename}")
            print(f"File type: {file.file_type}")
            print(f"File path: {file.file_path}")
            
            if file.file_path:
                if file.file_path.startswith('gs://'):
                    print("✅ GCS URI")
                elif file.file_path.startswith('http'):
                    print("⚠️ HTTP URL")
                else:
                    print("❌ Local path")
            else:
                print("❌ No file_path")
            
            print(f"Company ID: {file.company_id}")
            print(f"Uploaded at: {file.uploaded_at}")
            print("-" * 60)

if __name__ == '__main__':
    check_uploaded_files()
