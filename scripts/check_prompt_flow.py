"""
Check prompt flow for manual generation
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app
from src.models.models import Manual, ManualTemplate
import json

def check_recent_manual():
    """Check the most recent manual's generation options"""
    with app.app_context():
        manual = Manual.query.order_by(Manual.id.desc()).first()
    
        if not manual:
            print("No manuals found")
            return
        
        print(f"\n=== Manual ID: {manual.id} ===")
        print(f"Title: {manual.title}")
        print(f"Template ID: {manual.template_id}")
        print(f"Status: {manual.generation_status}")
        
        # Check generation options
        gen_options = manual.get_generation_options()
        print(f"\n=== Generation Options ===")
        print(json.dumps(gen_options, indent=2, ensure_ascii=False))
        
        # Check template
        if manual.template_id:
            template = ManualTemplate.query.get(manual.template_id)
            if template:
                print(f"\n=== Template: {template.name} ===")
                print(f"Description: {template.description}")
                
                template_content = template.template_content
                if isinstance(template_content, str):
                    template_content = json.loads(template_content)
                
                print(f"\n=== Template Content ===")
                print(json.dumps(template_content, indent=2, ensure_ascii=False))

if __name__ == '__main__':
    check_recent_manual()
