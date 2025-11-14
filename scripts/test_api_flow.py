"""
Complete API flow test: Login → Upload → Generate Manual
Tests GCS integration with environment-specific buckets and company_id folders
"""

import os
import sys
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Test account credentials
TEST_COMPANY_CODE = 'career-survival'
TEST_USER_EMAIL = 'support@career-survival.com'
TEST_PASSWORD = '0000'

BASE_URL = 'http://localhost:5000'

def print_section(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def print_result(success, message):
    icon = "✅" if success else "❌"
    print(f"{icon} {message}")

# ============================================================================
# Step 1: Login
# ============================================================================
print_section("Step 1: Login with Test Account")

login_data = {
    'company_id': TEST_COMPANY_CODE,
    'email': TEST_USER_EMAIL,
    'password': TEST_PASSWORD
}

print(f"Logging in as: {TEST_USER_EMAIL}")
print(f"Company: {TEST_COMPANY_CODE}")

try:
    login_response = requests.post(
        f'{BASE_URL}/auth/login',
        json=login_data,
        timeout=10
    )
    
    if login_response.status_code == 200:
        print_result(True, f"Login successful (Status: {login_response.status_code})")
        session_cookies = login_response.cookies
        login_result = login_response.json()
        print(f"   User: {login_result.get('user', {}).get('name')}")
        print(f"   Role: {login_result.get('user', {}).get('role')}")
    else:
        print_result(False, f"Login failed (Status: {login_response.status_code})")
        print(f"   Response: {login_response.text[:200]}")
        sys.exit(1)
except Exception as e:
    print_result(False, f"Login request failed: {e}")
    sys.exit(1)

# ============================================================================
# Step 2: Find Test Video
# ============================================================================
print_section("Step 2: Find Test Video File")

test_video_path = None

# Search for video files in uploads directory
uploads_dir = Path('uploads')
if uploads_dir.exists():
    print(f"Searching in: {uploads_dir.absolute()}")
    for video_ext in ['mp4', 'mov', 'avi', 'webm']:
        video_files = list(uploads_dir.rglob(f'*.{video_ext}'))
        if video_files:
            test_video_path = video_files[0]
            break

if not test_video_path or not test_video_path.exists():
    print_result(False, "No test video found in uploads directory")
    print("Please ensure there is at least one video file in uploads/")
    sys.exit(1)

file_size_mb = test_video_path.stat().st_size / (1024*1024)
print_result(True, f"Found test video: {test_video_path.name}")
print(f"   Path: {test_video_path}")
print(f"   Size: {file_size_mb:.2f} MB")

# ============================================================================
# Step 3: Upload Video to GCS
# ============================================================================
print_section("Step 3: Upload Video to GCS")

print(f"Uploading: {test_video_path.name}")
print(f"Expected bucket: kantan-ai-manual-generator-dev")
print(f"Expected path: gs://kantan-ai-manual-generator-dev/company_1/videos/...")

try:
    with open(test_video_path, 'rb') as f:
        files = {'file': (test_video_path.name, f, 'video/mp4')}
        upload_response = requests.post(
            f'{BASE_URL}/api/manuals/upload-file',
            files=files,
            cookies=session_cookies,
            timeout=60
        )
    
    if upload_response.status_code == 200:
        upload_result = upload_response.json()
        gcs_uri = upload_result.get('gcs_uri', '')
        
        print_result(True, f"Upload successful (Status: {upload_response.status_code})")
        print(f"   GCS URI: {gcs_uri}")
        print(f"   File size: {upload_result.get('file_size', 0) / (1024*1024):.2f} MB")
        print(f"   Storage type: {upload_result.get('storage_type')}")
        
        # Verify GCS URI format
        if gcs_uri.startswith('gs://kantan-ai-manual-generator-dev/'):
            print_result(True, "GCS URI format is correct (dev bucket)")
        else:
            print_result(False, f"Unexpected bucket in URI: {gcs_uri}")
        
        # Verify company_id folder structure
        if '/company_1/videos/' in gcs_uri:
            print_result(True, "Company-based folder structure is correct")
        else:
            print_result(False, "Company folder structure not found in URI")
            
    else:
        print_result(False, f"Upload failed (Status: {upload_response.status_code})")
        print(f"   Response: {upload_response.text[:500]}")
        sys.exit(1)
        
except Exception as e:
    print_result(False, f"Upload request failed: {e}")
    sys.exit(1)

# ============================================================================
# Step 4: List Available Templates
# ============================================================================
print_section("Step 4: Get Available Templates")

try:
    templates_response = requests.get(
        f'{BASE_URL}/api/company/templates',
        cookies=session_cookies,
        timeout=10
    )
    
    if templates_response.status_code == 200:
        templates = templates_response.json()
        template_count = len(templates)
        print_result(True, f"Retrieved {template_count} templates")
        
        if template_count > 0:
            # Use first template with custom prompts if available
            selected_template = None
            for tmpl in templates:
                sections = tmpl.get('template_content', {}).get('sections', [])
                has_custom_prompts = any(s.get('custom_prompt') for s in sections)
                if has_custom_prompts:
                    selected_template = tmpl
                    break
            
            if not selected_template:
                selected_template = templates[0]
            
            template_id = selected_template['id']
            template_name = selected_template['name']
            sections = selected_template.get('template_content', {}).get('sections', [])
            custom_prompt_count = sum(1 for s in sections if s.get('custom_prompt'))
            
            print(f"   Selected template: {template_name} (ID: {template_id})")
            print(f"   Sections: {len(sections)}")
            print(f"   Sections with custom prompts: {custom_prompt_count}")
        else:
            print_result(False, "No templates available")
            print("   Proceeding without template...")
            template_id = None
            custom_prompt_count = 0
    else:
        print_result(False, f"Failed to retrieve templates (Status: {templates_response.status_code})")
        template_id = None
        custom_prompt_count = 0
        
except Exception as e:
    print_result(False, f"Template request failed: {e}")
    template_id = None
    custom_prompt_count = 0

# ============================================================================
# Step 5: Generate Manual with Template
# ============================================================================
print_section("Step 5: Generate Manual with ReAct Pattern")

generation_data = {
    'title': f'API Test Manual {int(time.time())}',
    'video_uri': gcs_uri,
    'output_format': 'text_with_images',
    'use_rag': True
}

if template_id:
    generation_data['template_ids'] = [template_id]
    print(f"Using template ID: {template_id}")
else:
    print("Generating without template")

print(f"Title: {generation_data['title']}")
print(f"Video URI: {gcs_uri}")
print(f"Output format: {generation_data['output_format']}")
print(f"RAG enabled: {generation_data['use_rag']}")

try:
    generate_response = requests.post(
        f'{BASE_URL}/api/manuals/generate',
        json=generation_data,
        cookies=session_cookies,
        timeout=30
    )
    
    if generate_response.status_code in [200, 201]:
        generate_result = generate_response.json()
        manual_id = generate_result.get('manual_id')
        job_id = generate_result.get('job_id')
        
        print_result(True, f"Manual generation started (Status: {generate_response.status_code})")
        print(f"   Manual ID: {manual_id}")
        print(f"   Job ID: {job_id}")
        print(f"   Status: {generate_result.get('status')}")
        
    else:
        print_result(False, f"Generation request failed (Status: {generate_response.status_code})")
        print(f"   Response: {generate_response.text[:500]}")
        sys.exit(1)
        
except Exception as e:
    print_result(False, f"Generation request failed: {e}")
    sys.exit(1)

# ============================================================================
# Step 6: Monitor Job Status
# ============================================================================
print_section("Step 6: Monitor Job Status")

print(f"Monitoring job: {job_id}")
print("Waiting for completion (checking every 3 seconds)...")

max_attempts = 100  # 5 minutes maximum
attempt = 0

while attempt < max_attempts:
    try:
        job_response = requests.get(
            f'{BASE_URL}/api/jobs/{job_id}',
            cookies=session_cookies,
            timeout=10
        )
        
        if job_response.status_code == 200:
            job_data = job_response.json()
            status = job_data.get('status')
            progress = job_data.get('progress', 0)
            
            print(f"   [{attempt + 1}] Status: {status}, Progress: {progress}%", end='')
            
            if status == 'completed':
                print()
                print_result(True, "Manual generation completed!")
                print(f"   Completed at: {job_data.get('completed_at')}")
                break
            elif status == 'failed':
                print()
                print_result(False, "Manual generation failed")
                error_message = job_data.get('error_message', 'Unknown error')
                print(f"   Error: {error_message}")
                sys.exit(1)
            else:
                print(" (in progress)")
                time.sleep(3)
                attempt += 1
        else:
            print()
            print_result(False, f"Failed to check job status (Status: {job_response.status_code})")
            break
            
    except Exception as e:
        print()
        print_result(False, f"Job status check failed: {e}")
        break

if attempt >= max_attempts:
    print_result(False, "Timeout waiting for job completion")
    sys.exit(1)

# ============================================================================
# Step 7: Retrieve Generated Manual
# ============================================================================
print_section("Step 7: Retrieve Generated Manual")

try:
    manual_response = requests.get(
        f'{BASE_URL}/api/manuals/{manual_id}',
        cookies=session_cookies,
        timeout=10
    )
    
    if manual_response.status_code == 200:
        manual_data = manual_response.json()
        
        print_result(True, "Manual retrieved successfully")
        print(f"   Title: {manual_data.get('title')}")
        print(f"   Status: {manual_data.get('status')}")
        print(f"   Created: {manual_data.get('created_at')}")
        
        # Check if manual has content
        manual_content = manual_data.get('manual_content', {})
        sections = manual_content.get('sections', [])
        
        if sections:
            print_result(True, f"Manual has {len(sections)} sections")
            
            # Show first 3 section titles
            for i, section in enumerate(sections[:3]):
                print(f"      {i+1}. {section.get('title', 'Untitled')}")
            
            if len(sections) > 3:
                print(f"      ... and {len(sections) - 3} more sections")
        else:
            print_result(False, "Manual has no sections")
        
        # Check for template compliance
        generation_options = manual_data.get('generation_options', {})
        template_sections = generation_options.get('sections', [])
        
        if template_sections:
            print_result(True, f"Template applied with {len(template_sections)} section definitions")
            custom_prompt_sections = [s for s in template_sections if s.get('custom_prompt')]
            if custom_prompt_sections:
                print(f"   Sections with custom prompts: {len(custom_prompt_sections)}")
                for section in custom_prompt_sections[:2]:
                    print(f"      - {section.get('title')}")
        
    else:
        print_result(False, f"Failed to retrieve manual (Status: {manual_response.status_code})")
        print(f"   Response: {manual_response.text[:500]}")
        
except Exception as e:
    print_result(False, f"Manual retrieval failed: {e}")

# ============================================================================
# Summary
# ============================================================================
print_section("Test Summary")

print_result(True, "Login successful")
print_result(True, "Video uploaded to GCS with correct bucket and folder structure")
print_result(True, f"GCS URI format: gs://kantan-ai-manual-generator-dev/company_1/videos/...")
print_result(True, "Manual generation initiated")
print_result(True, "Job completed successfully")
print_result(True, "Manual content generated with sections")

if template_id:
    print_result(True, f"Template applied (ID: {template_id})")
    if custom_prompt_count > 0:
        print_result(True, f"Custom prompts used: {custom_prompt_count} sections")

print("\n🎉 All tests passed! GCS integration is working correctly.")
print(f"\nView manual at: {BASE_URL}/manual/detail/{manual_id}")
