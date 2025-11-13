"""
Display manual content summary
"""
from src.models.models import db, Manual
from src.core.app import app

app.app_context().push()

manuals = [14, 13]

for manual_id in manuals:
    manual = Manual.query.get(manual_id)
    if manual:
        print(f"\n{'='*70}")
        print(f"Manual ID: {manual_id}")
        print(f"Title: {manual.title}")
        print(f"Status: {manual.generation_status}")
        print(f"Created: {manual.created_at}")
        print(f"Completed: {manual.completed_at}")
        print(f"Content Length: {len(manual.content) if manual.content else 0} chars")
        
        if manual.content:
            print(f"\n--- CONTENT PREVIEW (first 500 chars) ---")
            print(manual.content[:500])
            print(f"\n--- CONTENT PREVIEW (last 300 chars) ---")
            print(manual.content[-300:])
        else:
            print("No content generated")
        
        print(f"{'='*70}\n")
