"""
File: migrate_sqlite_to_postgresql.py
Purpose: Migrate all data from SQLite to PostgreSQL
Main functionality: Complete data migration preserving relationships
Dependencies: SQLAlchemy, sqlite3, PostgreSQL
"""

import sys
import os
from datetime import datetime

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app
from src.models.models import db
from sqlalchemy import create_engine, MetaData, Table, text, inspect
from sqlalchemy.orm import sessionmaker

def migrate_sqlite_to_postgresql():
    """
    Migrate all data from SQLite to PostgreSQL
    
    CRITICAL: This migration preserves all relationships and constraints
    """
    
    print("=" * 80)
    print("SQLite to PostgreSQL DATA MIGRATION")
    print("=" * 80)
    print()
    
    # SQLite source database
    sqlite_path = 'instance/manual_generator.db'
    if not os.path.exists(sqlite_path):
        print(f"❌ SQLite database not found: {sqlite_path}")
        return False
    
    sqlite_url = f'sqlite:///{sqlite_path}'
    
    with app.app_context():
        # Get PostgreSQL connection
        pg_url = app.config['SQLALCHEMY_DATABASE_URI']
        
        if 'sqlite' in pg_url.lower():
            print("❌ ERROR: Application is still configured for SQLite")
            print(f"   Current DATABASE_URL: {pg_url}")
            print()
            print("   Please ensure .env has:")
            print("   DATABASE_URL=postgresql://kantan_user:kantan_password@localhost:5432/kantan_ai_manual_generator")
            return False
        
        print(f"📂 Source (SQLite): {sqlite_path}")
        print(f"🐘 Target (PostgreSQL): {pg_url.split('@')[1] if '@' in pg_url else pg_url}")
        print()
        
        # Confirm migration
        response = input("⚠️  This will REPLACE all data in PostgreSQL. Continue? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Migration cancelled")
            return False
        
        print()
        print("🔄 Starting migration...")
        print()
        
        try:
            # Create engines
            sqlite_engine = create_engine(sqlite_url)
            pg_engine = db.engine
            
            # Get table order (respecting foreign keys)
            inspector = inspect(sqlite_engine)
            sqlite_tables = inspector.get_table_names()
            
            # Define migration order (respecting foreign key constraints)
            migration_order = [
                'super_admins',
                'companies',
                'users',
                'user_sessions',
                'uploaded_files',
                'manual_templates',
                'processing_jobs',  # Must be before manuals (foreign key reference)
                'manuals',
                'manual_pdfs',
                'manual_translations',
                'manual_source_files',
                'reference_materials',
                'reference_chunks',
                'activity_logs',
                'media'
            ]
            
            # Add any tables not in the predefined order
            for table in sqlite_tables:
                if table not in migration_order and table != 'sqlite_sequence':
                    migration_order.append(table)
            
            # Create sessions
            SqliteSession = sessionmaker(bind=sqlite_engine)
            sqlite_session = SqliteSession()
            
            metadata = MetaData()
            
            total_migrated = 0
            
            for table_name in migration_order:
                if table_name == 'sqlite_sequence':
                    continue
                
                if table_name not in sqlite_tables:
                    print(f"  ⊘ {table_name:<25} : Not in source database")
                    continue
                
                try:
                    # Reflect table from SQLite
                    sqlite_table = Table(table_name, metadata, autoload_with=sqlite_engine)
                    
                    # Get data from SQLite
                    result = sqlite_session.execute(text(f"SELECT * FROM {table_name}"))
                    rows = result.fetchall()
                    
                    if len(rows) == 0:
                        print(f"  ⊘ {table_name:<25} : 0 records (skipped)")
                        continue
                    
                    # Clear existing data in PostgreSQL
                    db.session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
                    db.session.commit()
                    
                    # Get column names
                    columns = [col.name for col in sqlite_table.columns]
                    
                    # Prepare insert statement
                    placeholders = ', '.join([f':{col}' for col in columns])
                    column_list = ', '.join(columns)
                    insert_sql = f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})"
                    
                    # Insert data in batches
                    batch_size = 100
                    inserted = 0
                    
                    for i in range(0, len(rows), batch_size):
                        batch = rows[i:i+batch_size]
                        
                        for row in batch:
                            # Convert row to dictionary
                            row_dict = {}
                            for idx, col in enumerate(columns):
                                value = row[idx]
                                
                                # Convert SQLite integer booleans (1/0) to Python booleans for PostgreSQL
                                if col in ['is_active', 'is_default', 'is_public'] and value is not None:
                                    value = bool(value)
                                
                                row_dict[col] = value
                            
                            db.session.execute(text(insert_sql), row_dict)
                            inserted += 1
                        
                        db.session.commit()
                    
                    # Update sequence for PostgreSQL (for auto-increment fields)
                    try:
                        # Get max ID
                        result = db.session.execute(text(f"SELECT MAX(id) FROM {table_name}"))
                        max_id = result.scalar()
                        
                        if max_id is not None:
                            # Update sequence
                            db.session.execute(text(
                                f"SELECT setval(pg_get_serial_sequence('{table_name}', 'id'), {max_id}, true)"
                            ))
                            db.session.commit()
                    except:
                        pass  # Table might not have an id column
                    
                    total_migrated += inserted
                    print(f"  ✓ {table_name:<25} : {inserted:>6} records migrated")
                    
                except Exception as e:
                    print(f"  ✗ {table_name:<25} : ERROR - {e}")
                    db.session.rollback()
                    continue
            
            sqlite_session.close()
            
            print()
            print("=" * 80)
            print(f"✅ MIGRATION COMPLETED SUCCESSFULLY")
            print("=" * 80)
            print(f"Total Records Migrated: {total_migrated:,}")
            print()
            
            # Verify migration
            print("🔍 Verifying migration...")
            print()
            
            for table_name in migration_order:
                if table_name == 'sqlite_sequence':
                    continue
                
                if table_name not in sqlite_tables:
                    continue
                
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    pg_count = result.scalar()
                    
                    result = sqlite_session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                    sqlite_count = result.scalar()
                    
                    if pg_count != sqlite_count:
                        print(f"  ⚠️  {table_name:<25} : SQLite={sqlite_count}, PostgreSQL={pg_count} (MISMATCH)")
                    elif pg_count > 0:
                        print(f"  ✓ {table_name:<25} : {pg_count} records verified")
                except Exception as e:
                    print(f"  ✗ {table_name:<25} : Verification failed - {e}")
            
            print()
            print("Next steps:")
            print("  1. Test application with PostgreSQL")
            print("  2. Verify all functionality works correctly")
            print("  3. Keep SQLite backup until confident in migration")
            
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = migrate_sqlite_to_postgresql()
    sys.exit(0 if success else 1)
