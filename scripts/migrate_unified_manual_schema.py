"""
File: migrate_unified_manual_schema.py
Purpose: Database migration for unified manual generation (Phase 6)
Main functionality: Add multi-format support fields to Manual model
Dependencies: SQLAlchemy, sqlite3
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.db_manager import db
from src.core import app as flask_app
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def migrate_schema():
    """
    Add new columns for unified manual generation system
    
    New fields:
    - output_format: Output format type
    - content_text: Plain text content
    - content_html: HTML formatted content
    - content_video_uri: Subtitle video URI
    - extracted_images: JSON image extraction info
    - video_clips: JSON video clip info
    - subtitles_data: JSON subtitle data
    - generation_options: JSON user options
    """
    
    with flask_app.app.app_context():
        try:
            # Check if columns already exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('manuals')]
            
            logger.info(f"Existing columns: {columns}")
            
            # List of new columns to add
            new_columns = {
                'output_format': "VARCHAR(50) DEFAULT 'text_with_images'",
                'content_text': "TEXT",
                'content_html': "TEXT",
                'content_video_uri': "VARCHAR(500)",
                'extracted_images': "TEXT",
                'video_clips': "TEXT",
                'subtitles_data': "TEXT",
                'generation_options': "TEXT"
            }
            
            # Add missing columns
            for col_name, col_type in new_columns.items():
                if col_name not in columns:
                    logger.info(f"Adding column: {col_name}")
                    with db.engine.connect() as conn:
                        conn.execute(db.text(f"ALTER TABLE manuals ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                else:
                    logger.info(f"Column {col_name} already exists, skipping")
            
            logger.info("Schema migration completed successfully")
            
        except Exception as e:
            logger.error(f"Migration failed: {str(e)}")
            raise


if __name__ == '__main__':
    migrate_schema()
