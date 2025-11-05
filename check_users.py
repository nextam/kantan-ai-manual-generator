"""Check User model fields"""
import sys
import os
project_root = os.path.abspath('.')
sys.path.insert(0, project_root)

from src.core.app import app
from src.models.models import db, User

with app.app_context():
    users = User.query.filter_by(company_id=1).all()
    print(f"Users in company 1: {len(users)}")
    for u in users:
        print(f"  ID: {u.id}")
        print(f"  username: {getattr(u, 'username', 'N/A')}")
        print(f"  email: {u.email}")
        print(f"  role: {u.role}")
        print(f"  is_active: {u.is_active}")
        print()
