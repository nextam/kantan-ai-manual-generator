-- Create test account for career-survival
-- Company ID: career-survival
-- User: support@career-survival.com
-- Password: 0000

-- First, check if company exists
SELECT * FROM companies WHERE company_code = 'career-survival';

-- Create company if not exists (password hash for '0000')
INSERT OR IGNORE INTO companies (name, company_code, password_hash, created_at, updated_at, is_active, settings)
VALUES (
    'Career Survival Inc.',
    'career-survival',
    'scrypt:32768:8:1$wkeFi249ld2q1CKZ$e7864eb06e0e1f57dbfe2b7d11d386a9c848880636e315ea9c6d5e019c6bce4740dec0cf6ff0b5c842cf1f667fbfb8e3a18599f1d5d1a01a368e2789fec51e9e',
    datetime('now'),
    datetime('now'),
    1,
    '{"manual_format": "standard", "ai_model": "gemini-2.5-pro", "storage_quota_gb": 100, "max_users": 50}'
);

-- Get company_id
SELECT id FROM companies WHERE company_code = 'career-survival';

-- Create user if not exists
-- Replace <COMPANY_ID> with actual ID from previous query
INSERT OR IGNORE INTO users (username, email, company_id, role, last_login, created_at, is_active)
SELECT 
    'support@career-survival.com',
    'support@career-survival.com',
    id,
    'admin',
    NULL,
    datetime('now'),
    1
FROM companies 
WHERE company_code = 'career-survival';

-- Verify creation
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
WHERE c.company_code = 'career-survival';
