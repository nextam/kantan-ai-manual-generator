"""
File: verify_test_setup.py
Purpose: Verify test account and template setup before manual generation
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.models.models import db, User, Company, ManualTemplate
from src.core.db_manager import create_app

def verify_setup():
    """Verify test account and template configuration."""
    app = create_app()
    with app.app_context():
        return _check_setup()

def _check_setup():
    """Internal function to check setup."""
    
    print("=== Test Account Verification ===")
    company = Company.query.filter_by(company_code='career-survival').first()
    if not company:
        print("❌ Company 'career-survival' not found")
        return False
    print(f"✅ Company found: {company.name}")
    
    user = User.query.filter_by(email='support@career-survival.com').first()
    if not user:
        print("❌ User 'support@career-survival.com' not found")
        return False
    print(f"✅ User found: {user.email}")
    print(f"   Role: {user.role}")
    print(f"   Company ID: {user.company_id}")
    
    print("\n=== Template Verification ===")
    templates = ManualTemplate.query.filter_by(company_id=company.id).all()
    print(f"Found {len(templates)} template(s)")
    
    for template in templates:
        print(f"\n📋 Template: {template.name}")
        print(f"   ID: {template.id}")
        print(f"   Created: {template.created_at}")
        
        # Check template content structure
        import json
        content = template.template_content
        if isinstance(content, str):
            try:
                content = json.loads(content)
            except:
                content = None
        
        if content and isinstance(content, dict) and 'sections' in content:
            sections = content['sections']
            print(f"   Sections: {len(sections)}")
            
            for i, section in enumerate(sections):
                title = section.get('title', 'N/A')
                custom_prompt = section.get('custom_prompt', '')
                prompt_length = len(custom_prompt) if custom_prompt else 0
                print(f"     [{i+1}] {title} (custom_prompt: {prompt_length} chars)")
        else:
            print("   ⚠️ No sections defined")
    
    if not templates:
        print("❌ No templates found for company")
        return False
    
    print("\n✅ Setup verification complete")
    return True

if __name__ == '__main__':
    try:
        success = verify_setup()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
