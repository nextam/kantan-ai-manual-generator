"""
File: check_manual_sources.py
Purpose: Check manual and source file relationships in database
"""
import sys
sys.path.insert(0, 'c:\\Users\\nekus\\github\\kantan-ai-manual-generator')

from src.models.models import db, Manual, ManualSourceFile, UploadedFile
from src.core.app import app

with app.app_context():
    manuals = Manual.query.limit(5).all()
    
    print("=== マニュアルとソースファイルの関連 ===\n")
    for manual in manuals:
        print(f"ID: {manual.id}")
        print(f"タイトル: {manual.title}")
        print(f"ステータス: {manual.generation_status}")
        
        sources = ManualSourceFile.query.filter_by(manual_id=manual.id).all()
        print(f"ソースファイル数: {len(sources)}")
        
        for source in sources:
            print(f"  - Role: {source.role}, File ID: {source.file_id}")
            if source.file:
                print(f"    File: {source.file.original_filename}, Path: {source.file.file_path}")
            else:
                print(f"    File: NOT FOUND")
        
        print()
