"""
Check if GCS buckets exist and create if needed
"""

import os
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv()

# Get credentials
credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', 'gcp-credentials.json')
print(f"Using credentials: {credentials_path}")
print(f"File exists: {os.path.exists(credentials_path)}")

# Set environment variable
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path

# Initialize client
client = storage.Client()

# Check buckets
dev_bucket_name = 'kantan-ai-manual-generator-dev'
live_bucket_name = 'kantan-ai-manual-generator-live'

print("\n=== Checking GCS Buckets ===\n")

# Check dev bucket
dev_bucket = client.bucket(dev_bucket_name)
dev_exists = dev_bucket.exists()
print(f"✓ {dev_bucket_name}: {'EXISTS' if dev_exists else 'NOT FOUND'}")

if not dev_exists:
    print(f"  Creating {dev_bucket_name}...")
    try:
        dev_bucket = client.create_bucket(dev_bucket_name, location='us-central1')
        print(f"  ✅ Created {dev_bucket_name}")
    except Exception as e:
        print(f"  ❌ Failed to create: {e}")

# Check live bucket
live_bucket = client.bucket(live_bucket_name)
live_exists = live_bucket.exists()
print(f"✓ {live_bucket_name}: {'EXISTS' if live_exists else 'NOT FOUND'}")

if not live_exists:
    print(f"  Creating {live_bucket_name}...")
    try:
        live_bucket = client.create_bucket(live_bucket_name, location='us-central1')
        print(f"  ✅ Created {live_bucket_name}")
    except Exception as e:
        print(f"  ❌ Failed to create: {e}")

print("\n=== Bucket Check Complete ===")
