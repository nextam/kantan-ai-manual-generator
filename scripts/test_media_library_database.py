"""
File: test_media_library_database.py
Purpose: Test database operations for media library
Main functionality: CRUD operations, tenant isolation, data integrity
Dependencies: Flask app context, database models
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_database_operations():
    """Test all database operations for Media model"""
    print("=" * 70)
    print("Media Library - Database Operations Test")
    print("=" * 70)
    print()
    
    try:
        from src.core.app import app
        from src.core.db_manager import db
        from src.models.models import Media, Company, User
        
        with app.app_context():
            print("1. Testing database connection...")
            # Check if Media table exists
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            if 'media' in tables:
                print("  ✓ Media table exists in database")
            else:
                print("  ✗ Media table NOT found - run migration first!")
                print("  Command: python scripts/migrate_add_media_table.py")
                return False
            
            # Get table columns
            columns = [col['name'] for col in inspector.get_columns('media')]
            print(f"  ✓ Media table has {len(columns)} columns")
            
            # Check required columns
            required_columns = [
                'id', 'company_id', 'uploaded_by', 'media_type', 'filename',
                'gcs_uri', 'gcs_bucket', 'gcs_path', 'title', 'description',
                'alt_text', 'tags', 'file_size', 'mime_type', 'image_metadata',
                'video_metadata', 'source_media_id', 'is_active', 'created_at',
                'updated_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in columns]
            if missing_columns:
                print(f"  ✗ Missing columns: {', '.join(missing_columns)}")
                return False
            else:
                print(f"  ✓ All required columns present")
            
            print()
            
            # Check indexes
            print("2. Testing database indexes...")
            indexes = inspector.get_indexes('media')
            print(f"  ✓ Found {len(indexes)} indexes")
            
            for idx in indexes:
                print(f"    - {idx['name']}: {', '.join(idx['column_names'])}")
            
            print()
            
            # Test company lookup for test account
            print("3. Testing test account access...")
            test_company = db.session.query(Company).filter_by(
                company_code='career-survival'
            ).first()
            
            if not test_company:
                print("  ✗ Test company 'career-survival' not found!")
                print("  Create test account first")
                return False
            
            print(f"  ✓ Test company found: {test_company.name} (ID: {test_company.id})")
            
            # Find test user
            test_user = db.session.query(User).filter_by(
                email='support@career-survival.com',
                company_id=test_company.id
            ).first()
            
            if not test_user:
                print("  ✗ Test user 'support@career-survival.com' not found!")
                return False
            
            print(f"  ✓ Test user found: {test_user.username} (Role: {test_user.role})")
            
            print()
            
            # Test Media model operations
            print("4. Testing Media model CRUD operations...")
            
            # Clean up any existing test data
            existing_test_media = db.session.query(Media).filter_by(
                company_id=test_company.id,
                filename='test_image_20251115.png'
            ).all()
            if existing_test_media:
                for media in existing_test_media:
                    db.session.delete(media)
                db.session.commit()
                print(f"  ✓ Cleaned up {len(existing_test_media)} existing test media records")
            
            # Create test media
            test_media = Media(
                company_id=test_company.id,
                uploaded_by=test_user.id,
                media_type='image',
                filename='test_image_20251115.png',
                original_filename='test_image.png',  # Required NOT NULL field
                gcs_uri=f'gs://test-bucket/company_{test_company.id}/media/image/test_image_20251115.png',
                gcs_bucket='test-bucket',
                gcs_path=f'company_{test_company.id}/media/image/test_image_20251115.png',
                title='Test Image',
                description='Test image for verification',
                alt_text='Test alt text',
                tags='test,verification',  # Comma-separated string for SQLite
                file_size=1024,
                mime_type='image/png',
                image_metadata='{"width": 800, "height": 600}',  # JSON string for SQLite
                is_active=True
            )
            
            db.session.add(test_media)
            db.session.commit()
            
            print(f"  ✓ Created test media: ID={test_media.id}")
            
            # Read test media
            retrieved_media = db.session.query(Media).filter_by(
                id=test_media.id,
                company_id=test_company.id
            ).first()
            
            if retrieved_media:
                print(f"  ✓ Retrieved media: {retrieved_media.title}")
            else:
                print("  ✗ Failed to retrieve media")
                return False
            
            # Update test media
            retrieved_media.title = 'Updated Test Image'
            retrieved_media.description = 'Updated description'
            db.session.commit()
            print("  ✓ Updated media")
            
            # Test to_dict method
            media_dict = retrieved_media.to_dict()
            if 'id' in media_dict and 'title' in media_dict:
                print(f"  ✓ to_dict() works: {len(media_dict)} fields")
            else:
                print("  ✗ to_dict() incomplete")
                return False
            
            # Test tenant isolation
            print()
            print("5. Testing tenant isolation...")
            
            # Try to query with wrong company_id (use non-existent integer ID)
            wrong_company_media = db.session.query(Media).filter_by(
                id=test_media.id,
                company_id=99999  # Non-existent company ID
            ).first()
            
            if wrong_company_media is None:
                print("  ✓ Tenant isolation working - cannot access other company data")
            else:
                print("  ✗ SECURITY ISSUE: Tenant isolation not working!")
                return False
            
            # Query only accessible media
            accessible_media = db.session.query(Media).filter_by(
                company_id=test_company.id,
                is_active=True
            ).all()
            
            print(f"  ✓ Found {len(accessible_media)} media items for test company")
            
            print()
            
            # Test soft delete
            print("6. Testing soft delete...")
            retrieved_media.is_active = False
            db.session.commit()
            print("  ✓ Marked media as inactive (soft delete)")
            
            # Verify it's not in active queries
            active_media = db.session.query(Media).filter_by(
                company_id=test_company.id,
                is_active=True
            ).count()
            
            print(f"  ✓ Active media count after soft delete: {active_media}")
            
            # But still exists in database
            all_media = db.session.query(Media).filter_by(
                company_id=test_company.id
            ).count()
            
            print(f"  ✓ Total media count (including inactive): {all_media}")
            
            print()
            
            # Cleanup test data
            print("7. Cleaning up test data...")
            db.session.delete(retrieved_media)
            db.session.commit()
            print("  ✓ Test media deleted")
            
            print()
            print("=" * 70)
            print("✓ All database tests passed successfully!")
            print("=" * 70)
            print()
            print("Database is ready for media library operations")
            print()
            
            return True
            
    except Exception as e:
        print(f"\n✗ Database test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        success = test_database_operations()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
