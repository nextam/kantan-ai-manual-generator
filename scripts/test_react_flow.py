"""
Test ReAct data flow
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.app import app
from src.models.models import Manual, ManualTemplate
import json

def test_react_flow():
    """Test if ReAct is triggered correctly"""
    with app.app_context():
        # Get latest manual
        manual = Manual.query.order_by(Manual.id.desc()).first()
        
        if not manual:
            print("No manuals found")
            return
        
        print(f"\n=== Manual ID: {manual.id} ===")
        print(f"Title: {manual.title}")
        
        # Get generation options
        gen_options = manual.get_generation_options()
        sections_config = gen_options.get('sections', [])
        
        print(f"\n=== Sections Config ===")
        print(f"Type: {type(sections_config)}")
        print(f"Length: {len(sections_config)}")
        
        if sections_config:
            print(f"First element type: {type(sections_config[0])}")
            print(f"First element: {sections_config[0]}")
        
        # Test the condition used in unified_manual_generator.py
        is_dict_list = isinstance(sections_config, list) and len(sections_config) > 0 and isinstance(sections_config[0], dict)
        print(f"\n=== Condition Test ===")
        print(f"isinstance(sections_config, list): {isinstance(sections_config, list)}")
        print(f"len(sections_config) > 0: {len(sections_config) > 0}")
        if sections_config:
            print(f"isinstance(sections_config[0], dict): {isinstance(sections_config[0], dict)}")
        print(f"FINAL: is_dict_list = {is_dict_list}")
        
        # What would sections_with_prompts be?
        sections_with_prompts = sections_config if is_dict_list else []
        print(f"\n=== Result ===")
        print(f"sections_with_prompts length: {len(sections_with_prompts)}")
        print(f"Would ReAct be triggered? {len(sections_with_prompts) > 0}")
        
        if sections_with_prompts:
            print(f"\n=== Sections with prompts ===")
            for i, section in enumerate(sections_with_prompts):
                print(f"Section {i}: {section.get('title')} - prompt length: {len(section.get('custom_prompt', ''))}")

if __name__ == '__main__':
    test_react_flow()
