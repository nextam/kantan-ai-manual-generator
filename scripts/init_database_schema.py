import sqlite3
from datetime import datetime

# Create database schema
conn = sqlite3.connect('instance/manual_generator.db')
cursor = conn.cursor()

# Create companies table
cursor.execute("""
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE,
    company_code VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    settings TEXT
)
""")

# Create users table
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) NOT NULL,
    email VARCHAR(120),
    company_id INTEGER NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    last_login DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE (username, company_id)
)
""")

# Create uploaded_files table
cursor.execute("""
CREATE TABLE IF NOT EXISTS uploaded_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    company_id INTEGER NOT NULL,
    uploaded_by INTEGER,
    uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    file_metadata TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (uploaded_by) REFERENCES users(id)
)
""")

# Create manuals table
cursor.execute("""
CREATE TABLE IF NOT EXISTS manuals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    content TEXT NOT NULL,
    manual_type VARCHAR(50) DEFAULT 'basic',
    company_id INTEGER NOT NULL,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    generation_status VARCHAR(20) DEFAULT 'pending',
    generation_progress INTEGER DEFAULT 0,
    error_message TEXT,
    stage1_content TEXT,
    stage2_content TEXT,
    stage3_content TEXT,
    generation_config TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
)
""")

# Create manual_source_files table
cursor.execute("""
CREATE TABLE IF NOT EXISTS manual_source_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    manual_id INTEGER NOT NULL,
    file_id INTEGER NOT NULL,
    role VARCHAR(50),
    FOREIGN KEY (manual_id) REFERENCES manuals(id),
    FOREIGN KEY (file_id) REFERENCES uploaded_files(id)
)
""")

# Create manual_templates table
cursor.execute("""
CREATE TABLE IF NOT EXISTS manual_templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    template_content TEXT NOT NULL,
    company_id INTEGER NOT NULL,
    created_by INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_default BOOLEAN DEFAULT 0,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    FOREIGN KEY (created_by) REFERENCES users(id)
)
""")

# Create user_sessions table
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    session_token VARCHAR(255) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    ip_address VARCHAR(45),
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
)
""")

# Create super_admins table
cursor.execute("""
CREATE TABLE IF NOT EXISTS super_admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    permission_level VARCHAR(20) DEFAULT 'full'
)
""")

conn.commit()

print("Database schema created successfully!")
print("\nTables created:")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
for table in cursor.fetchall():
    print(f"  - {table[0]}")

conn.close()
