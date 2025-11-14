"""
File: analyze_manual_22_content_structure.py
Purpose: Analyze content field structure to understand why image extraction failed
"""
import sqlite3
import json
import ast

conn = sqlite3.connect(r'instance\manual_generator.db')
cursor = conn.cursor()

cursor.execute("SELECT content FROM manuals WHERE id = 22")
row = cursor.fetchone()

if row and row[0]:
    content_str = row[0]
    
    print("=" * 70)
    print("📄 Content Field Structure Analysis")
    print("=" * 70)
    
    # Try to parse as JSON first
    try:
        content_dict = json.loads(content_str)
        print("✅ Valid JSON format")
        print(f"\nTop-level keys: {list(content_dict.keys())}")
        
        # Check for analysis_result
        if 'analysis_result' in content_dict:
            analysis = content_dict['analysis_result']
            print(f"\n✅ 'analysis_result' found")
            print(f"   Type: {type(analysis)}")
            
            if isinstance(analysis, dict):
                print(f"   Keys: {list(analysis.keys())}")
                
                # Check for steps
                if 'steps' in analysis:
                    steps = analysis['steps']
                    print(f"\n✅ 'steps' found: {len(steps)} steps")
                    
                    # Analyze first step
                    if steps:
                        first_step = steps[0]
                        print(f"\n📊 First step structure:")
                        print(f"   Keys: {list(first_step.keys())}")
                        
                        # Check frame_data
                        if 'frame_data' in first_step:
                            frame_data = first_step['frame_data']
                            print(f"\n✅ 'frame_data' found in first step")
                            print(f"   Type: {type(frame_data)}")
                            if isinstance(frame_data, dict):
                                print(f"   Keys: {list(frame_data.keys())}")
                                if 'image_base64' in frame_data:
                                    img_len = len(frame_data['image_base64'])
                                    print(f"\n✅ 'image_base64' found: {img_len} chars")
                                else:
                                    print(f"\n❌ 'image_base64' NOT in frame_data")
                        else:
                            print(f"\n❌ 'frame_data' NOT in first step")
                else:
                    print(f"\n❌ 'steps' NOT found in analysis_result")
        else:
            print(f"\n❌ 'analysis_result' NOT found")
            print(f"\nSearching for 'image_base64' in raw string...")
            
            # Manual search
            if 'image_base64' in content_str:
                # Find context around first occurrence
                idx = content_str.find('image_base64')
                context_start = max(0, idx - 200)
                context_end = min(len(content_str), idx + 200)
                context = content_str[context_start:context_end]
                
                print(f"\n📍 Found 'image_base64' at position {idx}")
                print(f"\n--- Context (200 chars before/after) ---")
                print(context)
                print(f"--- End Context ---\n")
            
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse failed: {e}")
        
        # Try Python literal eval
        try:
            content_dict = ast.literal_eval(content_str)
            print("\n✅ Valid Python dict (converted from string)")
            print(f"\nTop-level keys: {list(content_dict.keys())}")
            
            # Now analyze the structure
            if 'analysis_result' in content_dict:
                analysis = content_dict['analysis_result']
                print(f"\n✅ 'analysis_result' found")
                print(f"   Type: {type(analysis)}")
                
                if isinstance(analysis, dict):
                    print(f"   Keys: {list(analysis.keys())}")
                    
                    # Check for steps
                    if 'steps' in analysis:
                        steps = analysis['steps']
                        print(f"\n✅ 'steps' found: {len(steps)} steps")
                        
                        # Analyze first step
                        if steps:
                            first_step = steps[0]
                            print(f"\n📊 First step structure:")
                            print(f"   Type: {type(first_step)}")
                            print(f"   Keys: {list(first_step.keys())}")
                            
                            # Check frame_data
                            if 'frame_data' in first_step:
                                frame_data = first_step['frame_data']
                                print(f"\n✅ 'frame_data' found in first step")
                                print(f"   Type: {type(frame_data)}")
                                if isinstance(frame_data, dict):
                                    print(f"   Keys: {list(frame_data.keys())}")
                                    if 'image_base64' in frame_data:
                                        img_len = len(frame_data['image_base64'])
                                        print(f"\n✅✅✅ 'image_base64' FOUND: {img_len} chars")
                                    else:
                                        print(f"\n❌ 'image_base64' NOT in frame_data")
                                        print(f"   Available: {frame_data.keys()}")
                            else:
                                print(f"\n❌ 'frame_data' NOT in first step")
                                print(f"   Available keys: {first_step.keys()}")
                    else:
                        print(f"\n❌ 'steps' NOT found in analysis_result")
                        print(f"   Available keys: {analysis.keys()}")
            else:
                print(f"\n❌ 'analysis_result' NOT found")
        except Exception as e2:
            print(f"❌ Python literal_eval also failed: {e2}")
            
            # Show first 500 chars of raw content
            print(f"\n--- First 500 chars of raw content ---")
            print(content_str[:500])
            print(f"--- End ---")

else:
    print("❌ No content found for Manual 22")

conn.close()
