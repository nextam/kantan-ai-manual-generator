"""
Test manual generation with GCS video and template
"""
import requests
import time
import sys

BASE_URL = 'http://localhost:5000'
GCS_URI = 'gs://kantan-ai-manual-generator-dev/company_1/videos/ce0ca3b1-7936-4632-afec-5fce63c343e9_08935e03-81da-4292-9f4a-c10f3049d6cd_0111____VID_20250620_111337.mp4'

print("=== Manual Generation Test ===\n")

# Login
print("1. Logging in...")
response = requests.post(
    f'{BASE_URL}/auth/login',
    json={
        'company_id': 'career-survival',
        'email': 'support@career-survival.com',
        'password': '0000'
    }
)
if response.status_code != 200:
    print(f"❌ Login failed")
    sys.exit(1)
print("✅ Login successful")
cookies = response.cookies

# Get template
print("\n2. Getting template...")
response = requests.get(f'{BASE_URL}/api/company/templates', cookies=cookies)
if response.status_code == 200:
    templates_data = response.json()
    # Check if it's a list or dict with templates key
    templates = templates_data if isinstance(templates_data, list) else templates_data.get('templates', [])
    if templates and len(templates) > 0:
        template = templates[0]
        template_id = template['id']
        print(f"✅ Using template: {template['name']} (ID: {template_id})")
        sections = template.get('template_content', {}).get('sections', [])
        print(f"   Sections: {len(sections)}")
        custom_prompts = sum(1 for s in sections if s.get('custom_prompt'))
        print(f"   Custom prompts: {custom_prompts}")
    else:
        template_id = None
        print("⚠️ No templates found, proceeding without template")
else:
    template_id = None
    print("⚠️ Failed to get templates")

# Generate manual
print("\n3. Starting manual generation...")
generation_data = {
    'title': f'GCS Test Manual {int(time.time())}',
    'video_uri': GCS_URI,
    'output_format': 'text_with_images',
    'use_rag': True
}

if template_id:
    generation_data['template_ids'] = [template_id]

print(f"   Video URI: {GCS_URI}")
print(f"   Template: {'Yes (ID: ' + str(template_id) + ')' if template_id else 'No'}")

response = requests.post(
    f'{BASE_URL}/api/manuals/generate',
    json=generation_data,
    cookies=cookies
)

if response.status_code not in [200, 201]:
    print(f"❌ Generation failed: {response.status_code}")
    print(response.text[:500])
    sys.exit(1)

result = response.json()
manual_id = result.get('manual_id')
job_id = result.get('job_id')

print(f"✅ Generation started")
print(f"   Manual ID: {manual_id}")
print(f"   Job ID: {job_id}")

# Monitor progress
print("\n4. Monitoring progress...")
attempt = 0
max_attempts = 60

while attempt < max_attempts:
    response = requests.get(f'{BASE_URL}/api/jobs/{job_id}', cookies=cookies)
    if response.status_code == 200:
        job_data = response.json()
        status = job_data.get('status')
        progress = job_data.get('progress', 0)
        
        print(f"   [{attempt+1}] Status: {status}, Progress: {progress}%")
        
        if status == 'completed':
            print("\n✅ Generation completed!")
            break
        elif status == 'failed':
            error = job_data.get('error_message', 'Unknown error')
            print(f"\n❌ Generation failed: {error}")
            sys.exit(1)
        
        time.sleep(3)
        attempt += 1
    else:
        print(f"❌ Failed to check status")
        break

if attempt >= max_attempts:
    print("❌ Timeout")
    sys.exit(1)

# Get manual details
print("\n5. Retrieving manual...")
response = requests.get(f'{BASE_URL}/api/manuals/{manual_id}', cookies=cookies)
if response.status_code == 200:
    manual_data = response.json()
    print(f"✅ Manual retrieved")
    print(f"   Title: {manual_data.get('title')}")
    
    manual_content = manual_data.get('manual_content', {})
    sections = manual_content.get('sections', [])
    print(f"   Sections generated: {len(sections)}")
    
    if sections:
        print("\n   Section titles:")
        for i, section in enumerate(sections[:5], 1):
            print(f"      {i}. {section.get('title')}")
        if len(sections) > 5:
            print(f"      ... and {len(sections)-5} more")
    
    # Check template application
    gen_options = manual_data.get('generation_options', {})
    if gen_options.get('sections'):
        print(f"\n   ✅ Template was applied")
        print(f"   Template sections: {len(gen_options['sections'])}")
    
    print(f"\n🎉 Success! View at: {BASE_URL}/manual/detail/{manual_id}")
else:
    print(f"❌ Failed to retrieve manual")
