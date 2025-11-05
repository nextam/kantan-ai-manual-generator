"""
File: migrate_enterprise_schema.py
Purpose: Create new database tables for enterprise features
Main functionality: Database schema migration
Dependencies: SQLAlchemy, models
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.db_manager import db
from src.core.app import app
from src.models.models import (
    User, Company, ManualTemplate,
    ReferenceMaterial, ReferenceChunk, ActivityLog,
    ManualTranslation, ManualPDF, ProcessingJob
)
from sqlalchemy import text, inspect


def check_column_exists(engine, table_name, column_name):
    """Check if column exists in table"""
    inspector = inspect(engine)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def check_table_exists(engine, table_name):
    """Check if table exists"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def migrate_add_user_fields():
    """Add password_hash and language_preference to users table"""
    print("\n=== Migrating User table ===")
    
    with db.engine.connect() as conn:
        if not check_column_exists(db.engine, 'users', 'password_hash'):
            conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
            conn.commit()
            print("✓ Added password_hash to users table")
        else:
            print("- password_hash already exists")
        
        if not check_column_exists(db.engine, 'users', 'language_preference'):
            conn.execute(text("ALTER TABLE users ADD COLUMN language_preference VARCHAR(10) DEFAULT 'ja'"))
            conn.commit()
            print("✓ Added language_preference to users table")
        else:
            print("- language_preference already exists")


def migrate_add_template_fields():
    """Add updated_at and is_active to manual_templates table"""
    print("\n=== Migrating ManualTemplate table ===")
    
    if not check_table_exists(db.engine, 'manual_templates'):
        print("- manual_templates table does not exist yet")
        return
    
    with db.engine.connect() as conn:
        if not check_column_exists(db.engine, 'manual_templates', 'updated_at'):
            conn.execute(text("ALTER TABLE manual_templates ADD COLUMN updated_at DATETIME"))
            conn.commit()
            print("✓ Added updated_at to manual_templates table")
        else:
            print("- updated_at already exists")
        
        if not check_column_exists(db.engine, 'manual_templates', 'is_active'):
            conn.execute(text("ALTER TABLE manual_templates ADD COLUMN is_active BOOLEAN DEFAULT 1"))
            conn.commit()
            print("✓ Added is_active to manual_templates table")
        else:
            print("- is_active already exists")


def create_new_tables():
    """Create all new enterprise tables"""
    print("\n=== Creating new enterprise tables ===")
    
    tables_to_create = [
        'reference_materials',
        'reference_chunks',
        'activity_logs',
        'manual_translations',
        'manual_pdfs',
        'processing_jobs'
    ]
    
    inspector = inspect(db.engine)
    existing_tables = inspector.get_table_names()
    
    for table_name in tables_to_create:
        if table_name in existing_tables:
            print(f"- {table_name} already exists")
        else:
            print(f"+ Creating {table_name}...")
    
    db.create_all()
    print("✓ Created all new enterprise tables")


def create_indexes():
    """Create database indexes for performance"""
    print("\n=== Creating database indexes ===")
    
    with db.engine.connect() as conn:
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_user_action_date 
                ON activity_logs(user_id, action_type, created_at)
            """))
            print("✓ Created idx_user_action_date")
        except Exception as e:
            print(f"- idx_user_action_date: {str(e)}")
        
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_company_date 
                ON activity_logs(company_id, created_at)
            """))
            print("✓ Created idx_company_date")
        except Exception as e:
            print(f"- idx_company_date: {str(e)}")
        
        try:
            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_job_status_type 
                ON processing_jobs(job_status, job_type)
            """))
            print("✓ Created idx_job_status_type")
        except Exception as e:
            print(f"- idx_job_status_type: {str(e)}")
        
        conn.commit()
        print("✓ Created database indexes")


def verify_migration():
    """Verify that migration was successful"""
    print("\n=== Verifying migration ===")
    
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    required_tables = [
        'super_admins',
        'companies',
        'users',
        'manual_templates',
        'reference_materials',
        'reference_chunks',
        'activity_logs',
        'manual_translations',
        'manual_pdfs',
        'processing_jobs'
    ]
    
    missing_tables = [t for t in required_tables if t not in tables]
    
    if missing_tables:
        print(f"❌ Missing tables: {', '.join(missing_tables)}")
        return False
    
    print(f"✓ All {len(required_tables)} required tables exist")
    
    # Check User fields
    if check_column_exists(db.engine, 'users', 'password_hash'):
        print("✓ User.password_hash exists")
    else:
        print("❌ User.password_hash missing")
        return False
    
    if check_column_exists(db.engine, 'users', 'language_preference'):
        print("✓ User.language_preference exists")
    else:
        print("❌ User.language_preference missing")
        return False
    
    return True


if __name__ == '__main__':
    print("="*60)
    print("Starting Enterprise Schema Migration")
    print("="*60)
    
    with app.app_context():
        try:
            migrate_add_user_fields()
            migrate_add_template_fields()
            create_new_tables()
            create_indexes()
            
            if verify_migration():
                print("\n" + "="*60)
                print("✅ Migration completed successfully!")
                print("="*60)
            else:
                print("\n" + "="*60)
                print("⚠️ Migration completed with warnings")
                print("="*60)
        
        except Exception as e:
            print("\n" + "="*60)
            print(f"❌ Migration failed: {str(e)}")
            print("="*60)
            import traceback
            traceback.print_exc()
            sys.exit(1)
