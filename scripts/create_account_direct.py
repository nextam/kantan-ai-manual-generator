import sqlite3
from datetime import datetime

# Connect to database
conn = sqlite3.connect('instance/manual_generator.db')
cursor = conn.cursor()

# Password hash for '0000'
password_hash = 'scrypt:32768:8:1$wkeFi249ld2q1CKZ$e7864eb06e0e1f57dbfe2b7d11d386a9c848880636e315ea9c6d5e019c6bce4740dec0cf6ff0b5c842cf1f667fbfb8e3a18599f1d5d1a01a368e2789fec51e9e'

# Check if company exists
cursor.execute("SELECT id FROM companies WHERE company_code = ?", ('career-survival',))
result = cursor.fetchone()

if result:
    company_id = result[0]
    print(f"Company 'career-survival' already exists (ID: {company_id})")
else:
    # Create company
    cursor.execute("""
        INSERT INTO companies (name, company_code, password_hash, created_at, updated_at, is_active, settings)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        'Career Survival Inc.',
        'career-survival',
        password_hash,
        datetime.utcnow(),
        datetime.utcnow(),
        1,
        '{"manual_format": "standard", "ai_model": "gemini-2.5-pro", "storage_quota_gb": 100, "max_users": 50}'
    ))
    company_id = cursor.lastrowid
    print(f"Created company 'career-survival' (ID: {company_id})")

# Check if user exists
cursor.execute("SELECT id FROM users WHERE username = ? AND company_id = ?", 
               ('support@career-survival.com', company_id))
result = cursor.fetchone()

if result:
    user_id = result[0]
    print(f"User 'support@career-survival.com' already exists (ID: {user_id})")
else:
    # Create user
    cursor.execute("""
        INSERT INTO users (username, email, company_id, role, created_at, is_active)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        'support@career-survival.com',
        'support@career-survival.com',
        company_id,
        'admin',
        datetime.utcnow(),
        1
    ))
    user_id = cursor.lastrowid
    print(f"Created user 'support@career-survival.com' (ID: {user_id})")

# Commit changes
conn.commit()

# Verify creation
cursor.execute("""
    SELECT 
        c.id as company_id,
        c.name as company_name,
        c.company_code,
        u.id as user_id,
        u.username,
        u.email,
        u.role,
        u.is_active
    FROM companies c
    LEFT JOIN users u ON u.company_id = c.id
    WHERE c.company_code = 'career-survival'
""")

results = cursor.fetchall()
print("\nVerification:")
print("="*70)
for row in results:
    print(f"Company ID: {row[0]}")
    print(f"Company Name: {row[1]}")
    print(f"Company Code: {row[2]}")
    print(f"User ID: {row[3]}")
    print(f"Username: {row[4]}")
    print(f"Email: {row[5]}")
    print(f"Role: {row[6]}")
    print(f"Active: {row[7]}")
    print("="*70)

print("\nTest Account Credentials:")
print("="*70)
print("Company ID: career-survival")
print("User ID: support@career-survival.com")
print("Password: 0000")
print("Role: admin")
print("="*70)

conn.close()
