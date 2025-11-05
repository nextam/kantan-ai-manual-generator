import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import app
from src.models.models import db, Company, User

with app.app.app_context():
    company = Company.query.filter_by(company_code='career-survival').first()
    
    if not company:
        company = Company(name='Career Survival Inc.', company_code='career-survival')
        company.set_password('0000')
        company.set_settings({'manual_format': 'standard', 'ai_model': 'gemini-2.5-pro', 'storage_quota_gb': 100, 'max_users': 50})
        db.session.add(company)
        db.session.flush()
        print(f"Created company: career-survival (ID: {company.id})")
    else:
        print(f"Company exists: career-survival (ID: {company.id})")
    
    user = User.query.filter_by(username='support@career-survival.com', company_id=company.id).first()
    
    if not user:
        user = User(username='support@career-survival.com', email='support@career-survival.com', company_id=company.id, role='admin', is_active=True)
        db.session.add(user)
        db.session.commit()
        print(f"Created user: support@career-survival.com (ID: {user.id})")
    else:
        print(f"User exists: support@career-survival.com (ID: {user.id})")
    
    print("\nTest Account:")
    print("Company ID: career-survival")
    print("User ID: support@career-survival.com")
    print("Password: 0000")
    print("Role: admin")
