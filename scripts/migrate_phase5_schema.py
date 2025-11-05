"""
File: migrate_phase5_schema.py
Purpose: Database migration script for Phase 5 - Enhanced Manual Generation
Main functionality: Add fields to Manual model for template integration and RAG support
Dependencies: SQLAlchemy, models
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Initialize Flask app for database context
from src.core.app import app
from src.core.db_manager import db
from src.models.models import Manual, ManualTemplate, ProcessingJob
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_add_phase5_fields():
    """
    Add Phase 5 fields to manuals table:
    - template_id (FK to manual_templates)
    - video_uri (video URI path)
    - processing_job_id (FK to processing_jobs)
    - rag_sources (JSON: RAG sources used)
    - completed_at (timestamp when generation completed)
    """
    try:
        with app.app_context():
            # For SQLite, we need to check columns differently
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('manuals')]
            
            logger.info(f"Existing columns in manuals table: {existing_columns}")
            
            # SQLite doesn't support adding foreign keys after table creation
            # We'll add them as regular integer columns
            
            # Add template_id
            if 'template_id' not in existing_columns:
                db.session.execute(db.text("""
                    ALTER TABLE manuals 
                    ADD COLUMN template_id INTEGER
                """))
                logger.info("✓ Added template_id to manuals table")
            else:
                logger.info("  template_id already exists")
            
            # Add video_uri
            if 'video_uri' not in existing_columns:
                db.session.execute(db.text("""
                    ALTER TABLE manuals 
                    ADD COLUMN video_uri VARCHAR(500)
                """))
                logger.info("✓ Added video_uri to manuals table")
            else:
                logger.info("  video_uri already exists")
            
            # Add processing_job_id
            if 'processing_job_id' not in existing_columns:
                db.session.execute(db.text("""
                    ALTER TABLE manuals 
                    ADD COLUMN processing_job_id INTEGER
                """))
                logger.info("✓ Added processing_job_id to manuals table")
            else:
                logger.info("  processing_job_id already exists")
            
            # Add rag_sources
            if 'rag_sources' not in existing_columns:
                db.session.execute(db.text("""
                    ALTER TABLE manuals 
                    ADD COLUMN rag_sources TEXT
                """))
                logger.info("✓ Added rag_sources to manuals table")
            else:
                logger.info("  rag_sources already exists")
            
            # Add completed_at
            if 'completed_at' not in existing_columns:
                db.session.execute(db.text("""
                    ALTER TABLE manuals 
                    ADD COLUMN completed_at TIMESTAMP
                """))
                logger.info("✓ Added completed_at to manuals table")
            else:
                logger.info("  completed_at already exists")
            
            db.session.commit()
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Migration failed: {str(e)}")
        raise


def create_indexes():
    """Create database indexes for performance"""
    try:
        with app.app_context():
            # Index for template lookups
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_manuals_template_id 
                ON manuals(template_id)
            """))
            logger.info("✓ Created index on manuals.template_id")
            
            # Index for job lookups
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_manuals_processing_job_id 
                ON manuals(processing_job_id)
            """))
            logger.info("✓ Created index on manuals.processing_job_id")
            
            # Index for status and company queries
            db.session.execute(db.text("""
                CREATE INDEX IF NOT EXISTS idx_manuals_company_status 
                ON manuals(company_id, generation_status)
            """))
            logger.info("✓ Created index on manuals(company_id, generation_status)")
            
            db.session.commit()
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Index creation failed: {str(e)}")
        raise


def verify_migration():
    """Verify that migration was successful"""
    try:
        with app.app_context():
            inspector = db.inspect(db.engine)
            columns = inspector.get_columns('manuals')
            
            logger.info("\n=== Migration Verification ===")
            logger.info(f"All columns in manuals table:")
            
            phase5_columns = {}
            for col in columns:
                col_name = col['name']
                if col_name in ['template_id', 'video_uri', 'processing_job_id', 'rag_sources', 'completed_at']:
                    phase5_columns[col_name] = col['type']
                    logger.info(f"  - {col_name}: {col['type']}")
            
            expected_columns = {'template_id', 'video_uri', 'processing_job_id', 'rag_sources', 'completed_at'}
            actual_columns = set(phase5_columns.keys())
            
            if expected_columns == actual_columns:
                logger.info(f"\n✅ Migration verification PASSED - Found all {len(phase5_columns)} Phase 5 columns")
                return True
            else:
                missing = expected_columns - actual_columns
                logger.error(f"\n❌ Migration verification FAILED")
                logger.error(f"Missing columns: {missing}")
                return False
                
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}")
        return False


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("Phase 5 Database Migration - Enhanced Manual Generation")
    logger.info("=" * 60)
    
    try:
        # Run migration
        logger.info("\n[1/3] Adding Phase 5 fields to manuals table...")
        migrate_add_phase5_fields()
        
        logger.info("\n[2/3] Creating database indexes...")
        create_indexes()
        
        logger.info("\n[3/3] Verifying migration...")
        success = verify_migration()
        
        if success:
            logger.info("\n" + "=" * 60)
            logger.info("✅ Phase 5 migration completed successfully!")
            logger.info("=" * 60)
        else:
            logger.error("\n" + "=" * 60)
            logger.error("❌ Phase 5 migration completed with errors")
            logger.error("=" * 60)
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"\n❌ Migration failed with error: {str(e)}")
        sys.exit(1)
