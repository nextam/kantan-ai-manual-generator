"""
File: check_sqlite_data.py
Purpose: Check existing SQLite database data before migration
Main functionality: Count records in key tables
Dependencies: sqlite3
"""

import sqlite3
import os

def check_sqlite_data():
    """Check SQLite database for existing data"""
    
    db_path = 'instance/manual_generator.db'
    
    if not os.path.exists(db_path):
        print(f"❌ SQLite database not found at: {db_path}")
        return None
    
    print("=" * 80)
    print("SQLite Database Data Check")
    print("=" * 80)
    print(f"Database: {os.path.abspath(db_path)}")
    print(f"Size: {os.path.getsize(db_path) / 1024:.2f} KB")
    print()
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"📊 Total Tables: {len(tables)}")
        print()
        
        # Count data in key tables
        data_summary = {}
        key_tables = [
            'companies', 'users', 'manuals', 'uploaded_files', 
            'manual_templates', 'reference_materials', 'media'
        ]
        
        print("📈 Data Counts:")
        print("-" * 80)
        
        for table in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                data_summary[table] = count
                
                # Show details for key tables
                if table in key_tables or count > 0:
                    icon = "✓" if count > 0 else " "
                    print(f"  {icon} {table:<25} : {count:>6} records")
            except Exception as e:
                print(f"  ✗ {table:<25} : ERROR - {e}")
        
        print("-" * 80)
        
        # Total records
        total_records = sum(data_summary.values())
        print(f"\n📊 Total Records: {total_records:,}")
        
        # Check for actual data
        non_empty_tables = {k: v for k, v in data_summary.items() if v > 0}
        print(f"📊 Non-Empty Tables: {len(non_empty_tables)}")
        
        if total_records == 0:
            print("\n⚠️  WARNING: SQLite database is EMPTY - no data to migrate")
        else:
            print("\n✅ SQLite database contains data - migration needed")
        
        conn.close()
        
        return data_summary
        
    except Exception as e:
        print(f"❌ Error reading SQLite database: {e}")
        return None

if __name__ == '__main__':
    check_sqlite_data()
