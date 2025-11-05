"""Check S3 configuration"""
import os
from dotenv import load_dotenv

load_dotenv()

print(f"USE_S3: {os.getenv('USE_S3', 'NOT SET')}")
print(f"AWS_ACCESS_KEY_ID: {os.getenv('AWS_ACCESS_KEY_ID', 'NOT SET')[:20]}...")
print(f"AWS_REGION: {os.getenv('AWS_REGION', 'NOT SET')}")
print(f"S3_BUCKET_MATERIALS: {os.getenv('S3_BUCKET_MATERIALS', 'NOT SET')}")
