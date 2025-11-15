"""
File: init_postgresql_database.py
Purpose: Initialize PostgreSQL database with all required tables
Main functionality: Creates all tables including companies, users, manuals, and media
Dependencies: SQLAlchemy, Flask app context
"""

import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app
from src.models.models import db, Company, User, Manual, Media
from sqlalchemy import inspect, text

def check_database_exists():
    """Check if database connection is working"""
    try:
        with app.app_context():
            db.session.execute(text('SELECT 1'))
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def init_postgresql_database():
    """
    Initialize PostgreSQL database with all tables
    
    This creates:
    - companies table
    - users table
    - manuals table
    - manual_steps table
    - media table
    - All other application tables
    """
    
    print("=" * 80)
    print("PostgreSQL DATABASE INITIALIZATION")
    print("=" * 80)
    print()
    
    # Check database connection
    if not check_database_exists():
        print("❌ Cannot connect to database. Please check:")
        print("  1. PostgreSQL container is running: docker ps")
        print("  2. DATABASE_URL in .env is correct")
        print("  3. PostgreSQL credentials are correct")
        return False
    
    print("✅ Database connection successful")
    print()
    
    with app.app_context():
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        print(f"📊 Existing tables: {len(existing_tables)}")
        if existing_tables:
            for table in existing_tables:
                print(f"  - {table}")
            print()
        
        # Create all tables
        print("📋 Creating all database tables...")
        try:
            db.create_all()
            print("✅ All tables created successfully")
            print()
        except Exception as e:
            print(f"❌ Failed to create tables: {e}")
            return False
        
        # Verify tables were created
        inspector = inspect(db.engine)
        all_tables = inspector.get_table_names()
        
        print(f"📊 Total tables after creation: {len(all_tables)}")
        for table in sorted(all_tables):
            columns = inspector.get_columns(table)
            indexes = inspector.get_indexes(table)
            print(f"  ✓ {table}: {len(columns)} columns, {len(indexes)} indexes")
        print()
        
        # Check critical tables
        required_tables = ['companies', 'users', 'manuals', 'media']
        missing_tables = [t for t in required_tables if t not in all_tables]
        
        if missing_tables:
            print(f"⚠️  WARNING: Missing required tables: {missing_tables}")
            return False
        
        print("✅ All required tables present")
        print()
        
        # Create test company and user if they don't exist
        print("👤 Creating test account...")
        test_company = db.session.query(Company).filter_by(company_code='career-survival').first()
        
        if not test_company:
            test_company = Company(
                company_code='career-survival',
                name='Career Survival Inc.',
                is_active=True
            )
            test_company.set_password('0000')  # Company password
            db.session.add(test_company)
            db.session.commit()
            print(f"  ✓ Created test company: {test_company.name} (ID: {test_company.id})")
        else:
            print(f"  ✓ Test company exists: {test_company.name} (ID: {test_company.id})")
        
        test_user = db.session.query(User).filter_by(email='support@career-survival.com').first()
        
        if not test_user:
            test_user = User(
                username='support',
                email='support@career-survival.com',
                company_id=test_company.id,
                role='super_admin',
                is_active=True
            )
            test_user.set_password('0000')
            db.session.add(test_user)
            db.session.commit()
            print(f"  ✓ Created test user: {test_user.email} (Role: {test_user.role})")
        else:
            print(f"  ✓ Test user exists: {test_user.email} (Role: {test_user.role})")
        
        print()
        print("=" * 80)
        print("✅ POSTGRESQL INITIALIZATION COMPLETED SUCCESSFULLY")
        print("=" * 80)
        print()
        print("Database Info:")
        print(f"  Connection: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[1]}")
        print(f"  Total Tables: {len(all_tables)}")
        print(f"  Test Company: career-survival (ID: {test_company.id})")
        print(f"  Test User: support@career-survival.com (Password: 0000)")
        print()
        print("Next steps:")
        print("  1. Run database tests: python scripts/test_media_library_database.py")
        print("  2. Start the application")
        print("  3. Test media upload functionality")
        
        return True

if __name__ == '__main__':
    success = init_postgresql_database()
    sys.exit(0 if success else 1)
