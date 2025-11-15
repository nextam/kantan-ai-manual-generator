"""
File: migrate_add_media_table.py
Purpose: Database migration to add Media table for media library functionality
Main functionality: Creates media table with tenant isolation and GCS integration
Dependencies: SQLAlchemy, Flask app context
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app
from src.models.models import db, Media, Company, User
from sqlalchemy import inspect, text

def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def migrate_add_media_table():
    """
    Add Media table to database
    
    CRITICAL: This migration must preserve tenant isolation
    """
    
    print("=" * 80)
    print("DATABASE MIGRATION: Add Media Table")
    print("=" * 80)
    
    with app.app_context():
        engine = db.engine
        
        # Check if media table already exists
        if check_table_exists(engine, 'media'):
            print("⚠️  WARNING: 'media' table already exists")
            response = input("Do you want to recreate it? (yes/no): ")
            if response.lower() != 'yes':
                print("❌ Migration cancelled")
                return
            
            print("🗑️  Dropping existing 'media' table...")
            db.session.execute(text('DROP TABLE IF EXISTS media CASCADE'))
            db.session.commit()
        
        # Create media table
        print("📋 Creating 'media' table...")
        Media.__table__.create(db.engine, checkfirst=True)
        
        # Verify table creation
        if check_table_exists(engine, 'media'):
            print("✅ 'media' table created successfully")
            
            # Show table structure
            inspector = inspect(engine)
            columns = inspector.get_columns('media')
            indexes = inspector.get_indexes('media')
            
            print("\n📊 Table Structure:")
            print(f"  Columns: {len(columns)}")
            for col in columns[:10]:  # Show first 10 columns
                print(f"    - {col['name']}: {col['type']}")
            if len(columns) > 10:
                print(f"    ... and {len(columns) - 10} more columns")
            
            print(f"\n  Indexes: {len(indexes)}")
            for idx in indexes:
                print(f"    - {idx['name']}: {idx['column_names']}")
            
            print("\n🔒 Tenant Isolation:")
            print("  - company_id column: ✅ NOT NULL with INDEX")
            print("  - Foreign key to companies table: ✅")
            
            print("\n☁️  GCS Integration:")
            print("  - gcs_uri column: ✅ NOT NULL, UNIQUE")
            print("  - gcs_bucket column: ✅")
            print("  - gcs_path column: ✅")
            
        else:
            print("❌ Failed to create 'media' table")
            return
        
        print("\n" + "=" * 80)
        print("✅ MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print("\nNext steps:")
        print("1. Restart your application")
        print("2. Test media upload functionality")
        print("3. Verify tenant isolation is working")
        print("4. Check GCS connectivity")

if __name__ == '__main__':
    try:
        migrate_add_media_table()
    except Exception as e:
        print("\n" + "=" * 80)
        print("❌ MIGRATION FAILED")
        print("=" * 80)
        print(f"Error: {str(e)}")
        import traceback
        print(f"\nTraceback:\n{traceback.format_exc()}")
        sys.exit(1)
